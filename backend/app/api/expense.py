"""
小金库 (Golden Nest) - 支出申请路由

⚠️ 已废弃：此模块的所有功能已迁移至通用审批系统 (approval.py)

支出申请现在通过以下接口处理：
- 创建支出申请: POST /api/approval/expense
- 审批支出申请: POST /api/approval/{id}/approve 或 /reject
- 查看支出申请: GET /api/approval/list?request_type=expense

此文件保留仅为代码历史参考，不再提供任何路由。
"""

# 此文件已废弃，所有支出审批功能已合并到 approval.py
# 保留此文件是为了避免其他地方可能存在的导入引用