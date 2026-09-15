import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import Dashboard from './pages/Dashboard'
import RepositoryOverview from './pages/RepositoryOverview'
import Chat from './pages/Chat'
import Architecture from './pages/Architecture'
import CodeExplorer from './pages/CodeExplorer'
import Search from './pages/Search'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/repo/:repositoryId" element={<RepositoryOverview />} />
        <Route path="/repo/:repositoryId/chat" element={<Chat />} />
        <Route path="/repo/:repositoryId/architecture" element={<Architecture />} />
        <Route path="/repo/:repositoryId/explorer" element={<CodeExplorer />} />
        <Route path="/repo/:repositoryId/search" element={<Search />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
