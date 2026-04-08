import { useQuery } from '@tanstack/react-query'
import { fetchUserProgress, fetchDueCards } from '@/lib/api'
import { Flame, Star, BookOpen } from 'lucide-react'

export default function Progress() {
  const { data: progress } = useQuery({ queryKey: ['user-progress'], queryFn: fetchUserProgress })
  const { data: dueCards } = useQuery({ queryKey: ['due-cards'], queryFn: () => fetchDueCards(50) })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Tu Progreso</h1>

      {progress && (
        <div className="grid grid-cols-2 gap-4">
          <StatCard icon={<Star className="text-yellow-500" size={24} />} label="XP Total" value={progress.xp_total} />
          <StatCard icon={<Flame className="text-orange-500" size={24} />} label="Días seguidos" value={`${progress.streak_days} 🔥`} />
        </div>
      )}

      <div className="p-4 rounded-xl bg-white border border-gray-200">
        <h2 className="font-semibold mb-2 flex items-center gap-2"><BookOpen size={18} /> Tarjetas pendientes hoy</h2>
        {dueCards?.length === 0 ? (
          <p className="text-green-600 text-sm">¡Todo al día! Vuelve mañana.</p>
        ) : (
          <p className="text-gray-700">{dueCards?.length} tarjetas para repasar</p>
        )}
      </div>
    </div>
  )
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="flex flex-col items-center p-5 rounded-xl bg-white border border-gray-200">
      {icon}
      <div className="text-2xl font-bold mt-2">{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  )
}
