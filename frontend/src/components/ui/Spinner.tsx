import { cn } from '../../utils'

export default function Spinner({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'inline-block h-4 w-4 animate-spin rounded-full border-2 border-solid border-current border-r-transparent',
        className,
      )}
      role="status"
      aria-label="Loading"
    />
  )
}
