from pathlib import Path
import pypdfium2 as pdfium
import sys, json
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
selected={
'gb29541_2013':('14.',[3,4,5]),
'gb24500_2020':('11.',[3,4,5,6]),
'gb19576_2019':('16.',[3,4]),
'gb37479_2019':('15.',[3,4,5]),
'gb18613_2020':('2.',[4,5,8]),
'gb30254_2024':('3.',[5,7,18]),
'gb30253_2024':('4.',[5,6,7,8,19,51]),
'gb19153_2019':('5.',[5,13,14,16,17,18]),
'gb28381_2012':('9. GB 28381-2012',[3,4,5,6,8]),
'gb21454_2021':('17.',[3,4,5,7,8,9,10,11,12,13,14])}
for key,(prefix,pages) in selected.items():
    if len(sys.argv)>1 and key not in sys.argv[1:]: continue
    p=next(x for x in (ROOT/'标准原文').glob('*.pdf') if x.name.startswith(prefix))
    doc=pdfium.PdfDocument(p)
    print(key,len(doc))
    texts=[]
    for i in range(len(doc)):
        page=doc[i]; texts.append({'physical_page':i+1,'text':page.get_textpage().get_text_range()})
        if i+1 in pages:
            img=page.render(scale=1.8).to_pil()
            img.save(OUT/'tmp'/f'{key}_p{i+1}.png')
    (OUT/'tmp'/f'{key}_pdf_text.json').write_text(json.dumps(texts,ensure_ascii=False,indent=2),encoding='utf-8')
