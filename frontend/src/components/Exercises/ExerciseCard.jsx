import React from 'react';
import { Link } from 'react-router-dom';
import './ExerciseCard.css';

const LANG_ICONS = {
  python: '🐍',
  javascript: '🟨',
  java: '☕',
};

const DIFFICULTY_META = {
  facile:    { label: 'Facile',    cls: 'ec-badge--facile' },
  moyen:     { label: 'Moyen',     cls: 'ec-badge--moyen' },
  difficile: { label: 'Difficile', cls: 'ec-badge--difficile' },
};

const ExerciseCard = ({ exercise }) => {
  const diff = DIFFICULTY_META[exercise.difficulty] ?? { label: exercise.difficulty, cls: '' };

  return (
    <Link to={`/exercises/${exercise.id}`} className="ec-card">
      {/* Accent bar */}
      <span className={`ec-accent ec-accent--${exercise.difficulty}`} />

      <div className="ec-body">
        {/* Badges */}
        <div className="ec-badges">
          <span className={`ec-badge ${diff.cls}`}>{diff.label}</span>
          <span className="ec-badge ec-badge--lang">
            {LANG_ICONS[exercise.language] ?? '💻'} {exercise.language}
          </span>
          {exercise.ai_generated && (
            <span className="ec-badge ec-badge--ai">✨ IA</span>
          )}
        </div>

        {/* Titre */}
        <h3 className="ec-title">{exercise.title}</h3>

        {/* Description tronquée */}
        <p className="ec-desc">
          {exercise.description?.substring(0, 110)}
          {exercise.description?.length > 110 ? '…' : ''}
        </p>
      </div>

      {/* Footer */}
      <div className="ec-footer">
        <span className="ec-cta">Commencer →</span>
      </div>
    </Link>
  );
};

export default ExerciseCard;
