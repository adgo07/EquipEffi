"""产品页面。所有一级导航项都必须是这里的真实页面，不得有 placeholder。"""
from .analysis import AnalysisPage
from .batch import BatchPage
from .home import HomePage
from .records import RecordsPage
from .settings import SettingsPage
from .standards import StandardsPage

__all__ = ("AnalysisPage", "BatchPage", "HomePage", "RecordsPage",
           "SettingsPage", "StandardsPage")
