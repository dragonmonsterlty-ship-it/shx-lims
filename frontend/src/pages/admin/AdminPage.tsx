import ComingSoon from '../../components/ComingSoon'

export default function AdminPage() {
  return <ComingSoon title="系统管理" description="仅管理员可见" planned={['用户管理', '系统设置', '审计日志']} />
}
