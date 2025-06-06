import requests
from typing import Dict, Any, Optional, List
import json

class AnimeCalendarTool:
    def __init__(self):
        self.api_url = "https://api.bgm.tv/calendar"
        self.weekdays = {
            1: "星期一",
            2: "星期二", 
            3: "星期三",
            4: "星期四",
            5: "星期五",
            6: "星期六",
            7: "星期日"
        }
    
    def execute(self, weekday: Optional[int] = None, format: str = "simple") -> str:
        """
        执行番剧每日放送查询
        """
        try:
            # 获取API数据
            response = requests.get(
                self.api_url,
                headers={'accept': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            calendar_data = response.json()
            
            if weekday:
                # 返回指定星期的番剧
                return self._format_single_day(calendar_data, weekday, format)
            else:
                # 返回全周番剧
                return self._format_full_week(calendar_data, format)
                
        except requests.RequestException as e:
            return f"❌ API请求失败: {str(e)}"
        except Exception as e:
            return f"❌ 处理数据时出错: {str(e)}"
    
    def _format_single_day(self, data: List[Dict], weekday: int, format: str) -> str:
        """格式化单日番剧信息"""
        target_day = None
        for day in data:
            if day["weekday"]["id"] == weekday:
                target_day = day
                break
        
        if not target_day:
            return f"❌ 未找到{self.weekdays.get(weekday, '未知')}的番剧信息"
        
        weekday_name = target_day["weekday"]["cn"]
        items = target_day["items"]
        
        if not items:
            return f"📅 {weekday_name}\n暂无番剧播出"
        
        result = f"📅 {weekday_name} 番剧放送 ({len(items)} 部)\n\n"
        
        if format == "simple":
            for item in items[:10]:  # 限制显示前10部
                name = item.get("name_cn") or item.get("name", "无标题")
                score = item.get("rating", {}).get("score", "暂无")
                result += f"• {name} (评分: {score})\n"
        else:
            for item in items[:8]:  # 详细模式显示更少但信息更全
                name = item.get("name_cn") or item.get("name", "无标题")
                original_name = item.get("name", "")
                rating = item.get("rating", {})
                score = rating.get("score", "暂无")
                total = rating.get("total", 0)
                air_date = item.get("air_date", "未知")
                
                result += f"📺 {name}\n"
                if original_name and original_name != name:
                    result += f"   原名: {original_name}\n"
                result += f"   评分: {score}/10 ({total}人评价)\n"
                result += f"   播出日期: {air_date}\n\n"
        
        if len(items) > (10 if format == "simple" else 8):
            result += f"... 还有 {len(items) - (10 if format == 'simple' else 8)} 部作品"
        
        return result
    
    def _format_full_week(self, data: List[Dict], format: str) -> str:
        """格式化全周番剧信息"""
        result = "📺 本周番剧放送时间表\n\n"
        
        for day in data:
            weekday_name = day["weekday"]["cn"]
            items = day["items"]
            
            if format == "simple":
                result += f"📅 {weekday_name}: {len(items)}部\n"
                # 显示当天评分最高的前3部
                sorted_items = sorted(
                    items, 
                    key=lambda x: x.get("rating", {}).get("score", 0), 
                    reverse=True
                )
                for item in sorted_items[:3]:
                    name = item.get("name_cn") or item.get("name", "无标题")
                    score = item.get("rating", {}).get("score", "暂无")
                    result += f"  • {name} ({score})\n"
                result += "\n"
            else:
                result += f"📅 {weekday_name} ({len(items)}部)\n"
                for item in items[:5]:  # 每天最多显示5部
                    name = item.get("name_cn") or item.get("name", "无标题")
                    score = item.get("rating", {}).get("score", "暂无")
                    result += f"  • {name} (评分: {score})\n"
                if len(items) > 5:
                    result += f"  ... 还有{len(items) - 5}部\n"
                result += "\n"
        
        return result
