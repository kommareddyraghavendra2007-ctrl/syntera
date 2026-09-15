import { NavLink, useParams } from 'react-router-dom'
import {
  LayoutDashboard, MessageSquare, GitBranch,
  Search, Code2, Activity, ChevronRight,
} from 'lucide-react'
import { cn } from '../../utils'

const NAV_TOP = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', exact: true },
]

const NAV_REPO = (id: string) => [
  { to: `/repo/${id}`, icon: Activity, label: 'Overview', exact: true },
  { to: `/repo/${id}/chat`, icon: MessageSquare, label: 'Ask' },
  { to: `/repo/${id}/architecture`, icon: GitBranch, label: 'Architecture' },
  { to: `/repo/${id}/explorer`, icon: Code2, label: 'Code Explorer' },
  { to: `/repo/${id}/search`, icon: Search, label: 'Search' },
]

export default function Sidebar() {
  const { repositoryId } = useParams()

  return (
    <aside className="w-56 flex-shrink-0 bg-surface-secondary border-r border-surface-border flex flex-col">
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-surface-border">
        <span className="text-lg font-bold text-white tracking-tight">
          <span className="text-syntera-400">SYN</span>TERA
        </span>
      </div>

      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {NAV_TOP.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors',
                isActive
                  ? 'bg-syntera-900/60 text-syntera-300'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-surface-tertiary',
              )
            }
          >
            <Icon size={15} />
            {label}
          </NavLink>
        ))}

        {repositoryId && (
          <>
            <div className="pt-3 pb-1 px-3">
              <span className="text-[10px] uppercase tracking-widest text-gray-600 font-semibold">
                Repository
              </span>
            </div>
            {NAV_REPO(repositoryId).map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={label === 'Overview'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors',
                    isActive
                      ? 'bg-syntera-900/60 text-syntera-300'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-surface-tertiary',
                  )
                }
              >
                <Icon size={15} />
                {label}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      <div className="p-3 border-t border-surface-border">
        <p className="text-[10px] text-gray-600 text-center">
          Codebase Intelligence Platform
        </p>
      </div>
    </aside>
  )
}
