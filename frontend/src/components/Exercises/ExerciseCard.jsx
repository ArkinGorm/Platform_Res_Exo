import React from 'react';
import { Link } from 'react-router-dom';
import './ExerciseCard.css';

const difficultyColors = {
  facile: '#4caf50',
  moyen: '#ff9800',
  difficile: '#f44336'
};

const ExerciseCard = ({ exercise }) => {
  return (
    <Link to={`/exercises/${exercise.id}`} className="exercise-card">
      <h3>{exercise.title}</h3>
      <div className="exercise-meta">
        <span 
          className="difficulty"
          style={{ backgroundColor: difficultyColors[exercise.difficulty] }}
        >
          {exercise.difficulty}
        </span>
        <span className="language">{exercise.language}</span>
      </div>
      <p className="exercise-description">
        {exercise.description.substring(0, 100)}...
      </p>
    </Link>
  );
};

export default ExerciseCard;