import { useParams, Link } from 'react-router-dom'
import FlashcardGame from '@/components/games/FlashcardGame'
import ListenChooseGame from '@/components/games/ListenChooseGame'
import WordMatchGame from '@/components/games/WordMatchGame'
import MultipleChoiceGame from '@/components/games/MultipleChoiceGame'
import FillBlankGame from '@/components/games/FillBlankGame'
import UnscrambleGame from '@/components/games/UnscrambleGame'
import StoryModeGame from '@/components/games/StoryModeGame'
import DictadoGame from '@/components/games/DictadoGame'
import EscribirGame from '@/components/games/EscribirGame'
import HablarGame from '@/components/games/HablarGame'

const GAMES: Record<string, React.ComponentType> = {
  flashcard: FlashcardGame,
  'listen-choose': ListenChooseGame,
  'word-match': WordMatchGame,
  'multiple-choice': MultipleChoiceGame,
  'fill-blank': FillBlankGame,
  unscramble: UnscrambleGame,
  story: StoryModeGame,
  dictado: DictadoGame,
  escribir: EscribirGame,
  hablar: HablarGame,
}

const LABELS: Record<string, string> = {
  flashcard: 'Tarjetas',
  'listen-choose': 'Escuchar y Elegir',
  'word-match': 'Emparejar Palabras',
  'multiple-choice': 'Test',
  'fill-blank': 'Rellenar el Hueco',
  unscramble: 'Ordenar la Frase',
  story: 'Modo Historia',
  dictado: 'Dictado',
  escribir: 'Escribir',
  hablar: 'Hablar',
}

export default function Practice() {
  const { gameType = 'flashcard' } = useParams()
  const GameComponent = GAMES[gameType]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link
          to="/dashboard"
          className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          ← Inicio
        </Link>
        <h1 className="text-xl font-bold">{LABELS[gameType] ?? gameType}</h1>
      </div>
      {GameComponent ? (
        <GameComponent />
      ) : (
        <div className="rounded-xl bg-yellow-50 p-6 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300">
          Este juego está en construcción. ¡Vuelve pronto!
        </div>
      )}
    </div>
  )
}
