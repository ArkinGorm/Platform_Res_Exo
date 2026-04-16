import React, { useState, useEffect, useMemo } from 'react';
import { getExercises } from '../../services/api';
import ExerciseCard from './ExerciseCard';
import toast from 'react-hot-toast';
import './ExerciseList.css';

const DIFFICULTY_OPTIONS = [
  { value: 'all', label: 'Tous les niveaux' },
  { value: 'facile', label: 'Facile' },
  { value: 'moyen', label: 'Moyen' },
  { value: 'difficile', label: 'Difficile' },
];

const LANGUAGE_OPTIONS = [
  { value: 'all', label: 'Tous les langages' },
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'java', label: 'Java' },
];

const SearchIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
    strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

const ExerciseList = () => {
  const [exercises, setExercises] = useState([]);
  const [loading, setLoading] = useState(true);
  const [difficulty, setDifficulty] = useState('all');
  const [language, setLanguage] = useState('all');
  const [search, setSearch] = useState('');

  useEffect(() => { loadExercises(); }, []);

  const loadExercises = async () => {
    try {
      const response = await getExercises();
      // Gère pagination Django REST ({ results: [...] }) ou tableau direct
      const data = response.data?.results ?? response.data;
      setExercises(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Erreur lors du chargement des exercices');
    } finally {
      setLoading(false);
    }
  };

  const filtered = useMemo(() => exercises.filter(ex => {
    if (difficulty !== 'all' && ex.difficulty !== difficulty) return false;
    if (language !== 'all' && ex.language !== language) return false;
    if (search && !ex.title.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  }), [exercises, difficulty, language, search]);

  // Stats rapides
  const stats = useMemo(() => ({
    total: exercises.length,
    facile: exercises.filter(e => e.difficulty === 'facile').length,
    moyen: exercises.filter(e => e.difficulty === 'moyen').length,
    difficile: exercises.filter(e => e.difficulty === 'difficile').length,
  }), [exercises]);

  if (loading) {
    return (
      <div className="el-loading">
        <div className="el-spinner" />
        <p>Chargement des exercices…</p>
      </div>
    );
  }

  return (
    <div className="el-page">
      {/* Hero */}
      <div className="el-hero">
        <h1>Exercices de code</h1>
        <p>Entraîne-toi, progresse et maîtrise les algorithmes</p>

        {/* Stats pills */}
        <div className="el-stats">
          <span className="el-stat">
            <strong>{stats.total}</strong> exercices
          </span>
          <span className="el-stat el-stat--facile">
            <strong>{stats.facile}</strong> facile
          </span>
          <span className="el-stat el-stat--moyen">
            <strong>{stats.moyen}</strong> moyen
          </span>
          <span className="el-stat el-stat--difficile">
            <strong>{stats.difficile}</strong> difficile
          </span>
        </div>
      </div>

      {/* Barre de filtres */}
      <div className="el-toolbar">
        <div className="el-search">
          <SearchIcon />
          <input
            type="text"
            placeholder="Rechercher un exercice…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {search && (
            <button className="el-clear" onClick={() => setSearch('')}>✕</button>
          )}
        </div>

        <div className="el-filters">
          <select value={difficulty} onChange={e => setDifficulty(e.target.value)}>
            {DIFFICULTY_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <select value={language} onChange={e => setLanguage(e.target.value)}>
            {LANGUAGE_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Résultats */}
      <div className="el-results-info">
        {filtered.length} exercice{filtered.length !== 1 ? 's' : ''} trouvé{filtered.length !== 1 ? 's' : ''}
      </div>

      {filtered.length === 0 ? (
        <div className="el-empty">
          <span className="el-empty-icon">🔍</span>
          <p>Aucun exercice ne correspond à ta recherche.</p>
          <button onClick={() => { setSearch(''); setDifficulty('all'); setLanguage('all'); }}>
            Réinitialiser les filtres
          </button>
        </div>
      ) : (
        <div className="el-grid">
          {filtered.map(exercise => (
            <ExerciseCard key={exercise.id} exercise={exercise} />
          ))}
        </div>
      )}
    </div>
  );
};

export default ExerciseList;
