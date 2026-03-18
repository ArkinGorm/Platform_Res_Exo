import React, { useState, useEffect } from 'react';
import { getExercises } from '../../services/api';
import ExerciseCard from './ExerciseCard';
import toast from 'react-hot-toast';
import './ExerciseList.css';

const ExerciseList = () => {
  const [exercises, setExercises] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadExercises();
  }, []);

  const loadExercises = async () => {
    try {
      const response = await getExercises();
      setExercises(response.data);
    } catch (error) {
      toast.error('Erreur lors du chargement des exercices');
    } finally {
      setLoading(false);
    }
  };

  const filteredExercises = exercises.filter(ex => {
    if (filter !== 'all' && ex.difficulty !== filter) return false;
    if (search && !ex.title.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  if (loading) {
    return <div className="loading">Chargement...</div>;
  }

  return (
    <div className="exercise-list-container">
      <div className="exercise-header">
        <h1>Exercices disponibles</h1>
        <div className="filters">
          <input
            type="text"
            placeholder="Rechercher..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
          <select 
            value={filter} 
            onChange={(e) => setFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">Tous niveaux</option>
            <option value="facile">Facile</option>
            <option value="moyen">Moyen</option>
            <option value="difficile">Difficile</option>
          </select>
        </div>
      </div>

      <div className="exercises-grid">
        {filteredExercises.map(exercise => (
          <ExerciseCard key={exercise.id} exercise={exercise} />
        ))}
      </div>

      {filteredExercises.length === 0 && (
        <div className="no-exercises">
          Aucun exercice trouvé
        </div>
      )}
    </div>
  );
};

export default ExerciseList;