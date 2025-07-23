from fastmcp import FastMCP
from bgm_calendar import AnimeCalendarTool
from typing import Annotated, Literal
from pydantic import Field
from enum import IntEnum

mcp = FastMCP("AnimeCalendarTool")

# 定义星期枚举，提供更好的语义
class Weekday(IntEnum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7

anime_tool = AnimeCalendarTool()

@mcp.tool()
def get_anime_calendar(
    weekday: Annotated[
        Weekday | None,
        Field(
            description="选择查询的星期几",
            json_schema_extra={
                "enum_descriptions": {
                    1: "星期一",
                    2: "星期二", 
                    3: "星期三",
                    4: "星期四",
                    5: "星期五",
                    6: "星期六",
                    7: "星期日"
                }
            }
        )
    ] = None,
    format: Annotated[
        Literal["simple", "detailed"],
        Field(
            description="选择显示格式",
            json_schema_extra={
                "enum_descriptions": {
                    "simple": "简洁格式 - 仅显示番剧标题和播放时间",
                    "detailed": "详细格式 - 包含番剧描述、评分等完整信息"
                }
            }
        )
    ] = "simple"
) -> dict:
    """获取番剧每日放送日历信息
    
    这个工具可以帮您查询指定日期或整周的番剧放送安排。
    支持按星期几筛选，并提供简单和详细两种显示模式。
    
    使用示例:
    - 查询今天的番剧: get_anime_calendar(weekday=当前星期几)
    - 查询全周番剧: get_anime_calendar()
    - 获取详细信息: get_anime_calendar(format="detailed")
    """
    # 如果传入的是枚举值，转换为整数
    weekday_int = int(weekday) if weekday is not None else None
    return anime_tool.execute(weekday=weekday_int, format=format)

if __name__ == "__main__":
    mcp.run()
