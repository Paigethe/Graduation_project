import type { Role } from '../api/types'

export type LucideName =
  | 'activity'
  | 'alert-triangle'
  | 'bar-chart-3'
  | 'book-open'
  | 'brain-circuit'
  | 'clipboard-list'
  | 'database'
  | 'download'
  | 'filter'
  | 'file-text'
  | 'layout-dashboard'
  | 'message-circle'
  | 'plus'
  | 'search'
  | 'send'
  | 'shield-check'
  | 'sliders-horizontal'
  | 'sparkles'
  | 'user-round'
  | 'users'

export type MenuId =
  | 'dashboard'
  | 'knowledge'
  | 'survey'
  | 'report'
  | 'ai_chat'
  | 'students'
  | 'intervention'
  | 'consult'
  | 'analysis'
  | 'progress'
  | 'reports'
  | 'backup'
  | 'users'
  | 'security'
  | 'database'
  | 'college_risk'

export interface MenuItem {
  id: MenuId
  name: string
  icon: LucideName
}

export const ROLE_LABEL: Record<Role, string> = {
  student: '学生',
  counselor: '心理辅导员',
  college_admin: '二级学院管理员',
  sys_admin: '系统管理员',
}

export const MENU_CONFIG: Record<Role, MenuItem[]> = {
  student: [
    { id: 'dashboard', name: '系统首页', icon: 'layout-dashboard' },
    { id: 'knowledge', name: '心理知识库', icon: 'book-open' },
    { id: 'survey', name: '在线测评', icon: 'clipboard-list' },
    { id: 'report', name: '分析报告', icon: 'file-text' },
    { id: 'intervention', name: '干预建议', icon: 'shield-check' },
    { id: 'ai_chat', name: 'AI 咨询', icon: 'message-circle' },
    { id: 'consult', name: '人工咨询', icon: 'users' },
  ],
  counselor: [
    { id: 'dashboard', name: '辅导员工作台', icon: 'layout-dashboard' },
    { id: 'students', name: '学生档案管理', icon: 'users' },
    { id: 'intervention', name: '干预建议推送', icon: 'shield-check' },
    { id: 'consult', name: '咨询服务', icon: 'message-circle' },
  ],
  college_admin: [
    { id: 'dashboard', name: '学院看板', icon: 'bar-chart-3' },
    { id: 'analysis', name: '深度统计分析', icon: 'brain-circuit' },
    { id: 'progress', name: '干预进度监控', icon: 'shield-check' },
    { id: 'reports', name: '月度报表生成', icon: 'download' },
    { id: 'backup', name: '学院数据备份', icon: 'database' },
  ],
  sys_admin: [
    { id: 'dashboard', name: '运维状态监控', icon: 'activity' },
    { id: 'college_risk', name: '学院风险分析', icon: 'bar-chart-3' },
    { id: 'users', name: '用户与权限', icon: 'users' },
    { id: 'security', name: '操作日志审计', icon: 'shield-check' },
    { id: 'database', name: '数据库管理', icon: 'database' },
    { id: 'backup', name: '全局全量备份', icon: 'database' },
  ],
}

export function menuName(role: Role, id: MenuId): string {
  return MENU_CONFIG[role].find((m) => m.id === id)?.name ?? '概览'
}
