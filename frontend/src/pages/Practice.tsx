import { useParams, Link } from 'react-router-dom'
import FlashcardGame from '@/components/games/FlashcardGame'
import ListenChooseGame from '@/components/games/ListenChooseGame'
import WordMatchGame from '@/components/games/WordMatchGame'
import MultipleChoiceGame from '@/components/games/MultipleChoiceGame'

const GAMES: Record<string, React.ComponentType> = {
  flashcard: FlashcardGame,
  'listen-choose': ListenChooseGame,
  'word-match': WordMatchGame,
  'multiple-choice': MultipleChoiceGame,
}

const LABELS: Record<string, string> = {
  flashcard: 'Tarjetas',
  'listen-choose': 'Escuchar y Elegir',
  'word-match': 'Emparejar Palabras',
  'multiple-choice': 'Test',
  'fill-blank': 'Rellenar el Hueco',
  unscramble: 'Ordenar la Frase',
  story: 'Modo Historia',
}

export default function Practice() {
  const { gameType = 'flashcard' } = useParams()
  const GameComponent = GAMES[gameType]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link to="/dashboard" className="text-sm text-gray-500 hover:text-gray-700">← Inicio</Link>
        <h1 className="text-xl font-bold">{LABELS[gameType] ?? gameType}</h1>
      </div>
      {GameComponent ? (
        <GameComponent />
      ) : (
        <div className="p-6 rounded-xl bg-yellow-50 text-yellow-800">
          Este juego está en construcción. ¡Vuelve pronto!
        </div>
      )}
    </div>
  )
}
