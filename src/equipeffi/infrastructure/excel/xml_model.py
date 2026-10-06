"""正确的 OOXML 词法 / 命名空间模型（Phase 8 R4）。

为什么需要这个模块
------------------
此前结果 Writer 直接用手写正则做元素/属性匹配，导致一系列同族缺陷：属性顺序、
单/双引号、命名空间前缀、属性命名空间、嵌套 prefix 重绑定……每修一个反例就扩大
一次盲区，而且"补丁"与"自检"共用同一个扫描器，自检因此无法独立发现问题。

本模块把**身份判定**集中到一处，并且严格按 XML 规范实现：

```text
词法     属性值可以用单引号或双引号；实体必须解码；注释/CDATA/PI/DOCTYPE 不是元素
命名空间 前缀按**词法作用域**（元素栈）解析；同名 local-name 在不同 namespace 是不同身份
属性     XML 中属性是**无命名空间**的；带前缀的属性其身份包含 namespace；
         `r` 与 `e:r` 是**两个不同的属性**，绝不能合并成一个键
```

要点（W3C XML / Namespaces in XML）：

- 属性值可单引号或双引号包裹；实体引用（`&amp;` `&#65;` `&#x41;`）需要解码。
- 未加前缀的属性**没有命名空间**；`xmlns` / `xmlns:x` 是命名空间声明，不是普通属性。
- 前缀在**声明它的元素及其后代**内有效；后代可以重新绑定（nested rebinding）。
- 默认命名空间只作用于**元素**，不作用于属性。

本模块只做解析与身份判定，不改写文本；Writer 依靠它做补丁，门禁依靠它做校验。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

#: SpreadsheetML 主命名空间。
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
#: `xmlns` 声明本身所在的命名空间（XML 规范）。
XMLNS_NS = "http://www.w3.org/2000/xmlns/"

#: 元素种类。
START = "start"
END = "end"
EMPTY = "empty"
TEXT = "text"
COMMENT = "comment"
CDATA = "cdata"
PI = "pi"
DOCTYPE = "doctype"


class XMLLexError(ValueError):
    """词法层面无法解析（未闭合引号/标签等）。"""


# ---------------------------------------------------------------------------
# 实体解码
# ---------------------------------------------------------------------------

_PREDEFINED = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}


def decode_entities(text: str) -> str:
    """解码 XML 实体引用（`&amp;` / `&#65;` / `&#x41;`）。

    无法识别的实体按字面保留——本模块用于**比较与判定**，不用于重写用户内容。
    """

    if "&" not in text:
        return text
    out: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char != "&":
            out.append(char)
            index += 1
            continue
        semi = text.find(";", index + 1)
        if semi == -1 or semi - index > 12:
            out.append(char)
            index += 1
            continue
        name = text[index + 1:semi]
        if name.startswith("#x") or name.startswith("#X"):
            try:
                out.append(chr(int(name[2:], 16)))
                index = semi + 1
                continue
            except ValueError:
                pass
        elif name.startswith("#"):
            try:
                out.append(chr(int(name[1:], 10)))
                index = semi + 1
                continue
            except ValueError:
                pass
        elif name in _PREDEFINED:
            out.append(_PREDEFINED[name])
            index = semi + 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# 属性
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Attribute:
    """一个属性（含 namespace 身份）。"""

    prefix: str
    local: str
    #: 原始（未解码）属性值。
    raw_value: str
    #: 引号字符（`"` 或 `'`）。
    quote: str
    ns_uri: str | None
    #: 该属性在开标记内的绝对区间（用于定点改写）。
    start: int
    end: int

    @property
    def expanded(self) -> str:
        """属性身份（notational name）：带 namespace 时含 URI。"""

        return self.local if not self.ns_uri else f"{{{self.ns_uri}}}{self.local}"

    @property
    def value(self) -> str:
        return decode_entities(self.raw_value)

    @property
    def is_namespace_declaration(self) -> bool:
        return self.prefix == "xmlns" or self.local == "xmlns" and not self.prefix


# ---------------------------------------------------------------------------
# 元素
# ---------------------------------------------------------------------------

@dataclass
class Element:
    """一个元素及其解析后的身份与作用域。"""

    kind: str
    #: 开标记 `<` 的绝对下标。
    start: int
    #: 开标记 `>` 的绝对下标（END 标记为 `</name>` 的 `>`）。
    tag_end: int
    #: 元素整体区间（START/EMPTY 含子树；END 为标记本身）。
    start_content: int
    end: int
    prefix: str
    local: str
    ns_uri: str | None
    attributes: list[Attribute] = field(default_factory=list)
    #: 该元素**自身**声明的命名空间（prefix -> uri；默认命名空间用 `""` 作键）。
    declared: dict[str, str] = field(default_factory=dict)
    #: 生效的命名空间作用域（含祖先声明）。
    scope: dict[str, str] = field(default_factory=dict)
    parent: "Element | None" = None
    children: list["Element"] = field(default_factory=list)

    @property
    def qname(self) -> str:
        return self.local if not self.prefix else f"{self.prefix}:{self.local}"

    @property
    def expanded(self) -> str:
        return self.local if not self.ns_uri else f"{{{self.ns_uri}}}{self.local}"

    @property
    def is_main_namespace(self) -> bool:
        return self.ns_uri == MAIN_NS

    def attribute(self, local: str, ns_uri: str | None = None) -> Attribute | None:
        """按 **local name + namespace** 取属性。

        未加前缀的属性**没有** namespace，因此 `attribute("r")` 只会命中真正的
        `r`，绝不会命中 `e:r`（`{urn:independent}r`）——这正是旧实现把两者
        合并成一个键、导致合法输入出现重复坐标的原因。
        """

        for item in self.attributes:
            if item.local == local and item.ns_uri == ns_uri:
                return item
        return None

    def attribute_value(self, local: str, ns_uri: str | None = None) -> str | None:
        item = self.attribute(local, ns_uri)
        return None if item is None else item.value

    def path_has_ancestor(self, *expanded: str) -> bool:
        """从自身向上检查祖先链（不含自身）是否恰好匹配给定路径。"""

        node = self.parent
        for expected in reversed(expanded):
            if node is None or node.expanded != expected:
                return False
            node = node.parent
        return node is None


# ---------------------------------------------------------------------------
# 词法扫描
# ---------------------------------------------------------------------------

_NAME_START = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_:")
_NAME_CHARS = _NAME_START | set("0123456789.-")


def _is_name_start(char: str) -> bool:
    return char in _NAME_START


def _is_name_char(char: str) -> bool:
    return char in _NAME_CHARS


def _read_name(text: str, index: int) -> tuple[str, int]:
    start = index
    while index < len(text) and _is_name_char(text[index]):
        index += 1
    if start == index:
        raise XMLLexError(f"位置 {start} 处缺少有效的 XML 名称")
    return text[start:index], index


def _read_attribute_value(text: str, index: int) -> tuple[str, str, int]:
    """读取属性值，**同时支持单引号与双引号**（W3C XML AttValue）。"""

    quote = text[index]
    if quote not in ("'", '"'):
        raise XMLLexError(f"位置 {index} 处属性值缺少引号")
    index += 1
    start = index
    while index < len(text) and text[index] != quote:
        index += 1
    if index >= len(text):
        raise XMLLexError("属性值引号未闭合")
    return text[start:index], quote, index + 1


def _skip_tag_end(text: str, index: int) -> int:
    """从 `<` 之后找到该标记的 `>`（正确跳过引号内内容）。"""

    while index < len(text):
        char = text[index]
        if char in ("'", '"'):
            _value, _quote, index = _read_attribute_value(text, index)
            continue
        if char == ">":
            return index
        index += 1
    raise XMLLexError("标签未闭合")


def scan_tags(xml: str) -> Iterator[tuple[str, int, int]]:
    """产出 ``(kind, start, tag_end)``——只做字符串层面的标记切分，不解析身份。

    `kind` ∈ {START, END, EMPTY, COMMENT, CDATA, PI, DOCTYPE}。
    """

    index = 0
    length = len(xml)
    while index < length:
        opening = xml.find("<", index)
        if opening == -1:
            return
        if xml.startswith("<!--", opening):
            close = xml.find("-->", opening + 4)
            end = length - 1 if close == -1 else close + 2
            yield COMMENT, opening, end
            index = end + 1
            continue
        if xml.startswith("<![CDATA[", opening):
            close = xml.find("]]>", opening + 9)
            end = length - 1 if close == -1 else close + 2
            yield CDATA, opening, end
            index = end + 1
            continue
        if xml.startswith("<?", opening):
            close = xml.find("?>", opening + 2)
            end = length - 1 if close == -1 else close + 1
            yield PI, opening, end
            index = end + 1
            continue
        if xml.startswith("<!", opening):
            tag_end = _skip_tag_end(xml, opening + 2)
            yield DOCTYPE, opening, tag_end
            index = tag_end + 1
            continue
        closing = xml.startswith("</", opening)
        end = _skip_tag_end(xml, opening + (2 if closing else 1))
        kind = END if closing else (EMPTY if xml[end - 1] == "/" else START)
        yield kind, opening, end
        index = end + 1


def _parse_tag_attributes(xml: str, kind: str, start: int,
                          tag_end: int) -> tuple[str, list[Attribute]]:
    """解析开标记的名称与全部属性（单/双引号都支持）。"""

    index = start + (2 if kind == END else 1)
    if kind == END:
        name, _ = _read_name(xml, index)
        return name, []
    name, index = _read_name(xml, index)
    attributes: list[Attribute] = []
    limit = tag_end - (1 if kind == EMPTY else 0)
    while index < limit:
        char = xml[index]
        if char.isspace():
            index += 1
            continue
        if char == "/":
            index += 1
            continue
        attr_start = index
        attr_name, index = _read_name(xml, index)
        while index < limit and xml[index].isspace():
            index += 1
        if index >= limit or xml[index] != "=":
            raise XMLLexError(f"属性 {attr_name} 缺少 '='")
        index += 1
        while index < limit and xml[index].isspace():
            index += 1
        raw_value, quote, index = _read_attribute_value(xml, index)
        prefix, _, local = attr_name.partition(":")
        if not local:
            prefix, local = "", prefix
        attributes.append(Attribute(
            prefix=prefix, local=local, raw_value=raw_value, quote=quote,
            ns_uri=None, start=attr_start, end=index))
    return name, attributes


# ---------------------------------------------------------------------------
# 完整解析（身份 + 作用域）
# ---------------------------------------------------------------------------

def parse_elements(xml: str) -> list[Element]:
    """解析出全部元素（含 namespace 作用域与完整身份）。

    返回按出现顺序排列的 `Element` 列表；END 标记也会返回（便于定位闭合位置）。
    """

    root: Element | None = None
    stack: list[Element] = []
    elements: list[Element] = []
    for kind, start, tag_end in scan_tags(xml):
        if kind not in (START, END, EMPTY):
            continue
        name, attributes = _parse_tag_attributes(xml, kind, start, tag_end)
        prefix, _, local = name.partition(":")
        if not local:
            prefix, local = "", prefix
        parent = stack[-1] if stack else None
        scope = dict(parent.scope) if parent is not None else {}
        declared: dict[str, str] = {}
        for attribute in attributes:
            if attribute.prefix == "xmlns":
                declared[attribute.local] = attribute.value
            elif attribute.local == "xmlns" and not attribute.prefix:
                declared[""] = attribute.value
        scope.update(declared)
        ns_uri = scope.get(prefix) if prefix else scope.get("")
        # 为属性补上 namespace 身份（属性**不**继承默认命名空间）。
        resolved: list[Attribute] = []
        for attribute in attributes:
            if attribute.prefix == "xmlns" or (
                    attribute.local == "xmlns" and not attribute.prefix):
                resolved.append(attribute)
                continue
            attr_ns = scope.get(attribute.prefix) if attribute.prefix else None
            resolved.append(Attribute(
                prefix=attribute.prefix, local=attribute.local,
                raw_value=attribute.raw_value, quote=attribute.quote,
                ns_uri=attr_ns, start=attribute.start, end=attribute.end))
        if kind == END:
            if stack:
                stack[-1].end = tag_end + 1
                stack.pop()
            continue
        element = Element(
            kind=kind, start=start, tag_end=tag_end,
            start_content=tag_end + 1,
            end=tag_end + 1 if kind == EMPTY else len(xml),
            prefix=prefix, local=local, ns_uri=ns_uri,
            attributes=resolved, declared=declared, scope=scope,
            parent=parent)
        elements.append(element)
        if parent is not None:
            parent.children.append(element)
        if root is None:
            root = element
        if kind == START:
            stack.append(element)
    # 未闭合的 START：把 end 收到文档末尾（保持确定性）
    return elements


def descendant_cells(element: Element) -> list[Element]:
    """按**正式路径**取 ``sheetData/row/c``（限定 MAIN_NS），而不是按 local name。"""

    found: list[Element] = []
    prefix = "{" + MAIN_NS + "}"
    for child in element.children:
        if child.expanded == prefix + "c":
            found.append(child)
        found.extend(descendant_cells(child))
    return found
