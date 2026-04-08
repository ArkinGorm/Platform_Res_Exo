import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getAdminExercises, publishExercise, unpublishExercise, deleteExercise
} from '../../services/api';
import toast from 'react-hot-toast';
import './AdminDashboard.css';

const AdminDashboard = () => {
  const [exercises, setExercises] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [filter, setFilter]       = useState('all'); // all | published | unpublished
  const navigate = useNavigate();

  useEffect(() => { loadExercises(); }, []);

  const loadExercises = async () => {
    try {
      const response = await getAdminExercises();
      setExercises(response.data.results ?? response.data);
    } catch {
      toast.error('Erreur lors du chargement des exercices');
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async (id, isPublished) => {
    try {
      if (isPublished) {
        await unpublishExercise(id);
        toast.success('Exercice dépublié');
      } else {
        await publishExercise(id);
        toast.success('Exercice publié !');
      }
      loadExercises();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Erreur');
    }
  };

  const handleDelete = async (id, title) => {
    if (!window.confirm(`Supprimer "${title}" ?`)) return;
    try {
      await deleteExercise(id);
      toast.success('Exercice supprimé');
      loadExercises();
    } catch {
      toast.error('Erreur lors de la suppression');
    }
  };

  const filtered = exercises.filter(ex => {
    if (filter === 'published')   return ex.is_published;
    if (filter === 'unpublished') return !ex.is_published;
    return true;
  });

  const difficultyLabel = { facile: 'Facile', moyen: 'Moyen', difficile: 'Difficile' };

  if (loading) return <div className="adm-loading">Chargement...</div>;

  return (
    <div className="adm-container">

      {/* Header */}
      <div className="adm-header">
        <div>
          <h1 className="adm-title">Dashboard Admin</h1>
          <p className="adm-subtitle">{exercises.length} exercice(s) au total</p>
        </div>
        <div className="adm-header-actions">
          <button className="adm-btn adm-btn-ai" onClick={() => navigate('/admin/generate')}>
            🤖 Générer via IA
          </button>
          <button className="adm-btn adm-btn-create" onClick={() => navigate('/admin/exercises/create')}>
            + Créer manuellement
          </button>
        </div>
      </div>

      {/* Filtres */}
      <div className="adm-filters">
        {[['all', 'Tous'], ['published', 'Publiés'], ['unpublished', 'Brouillons']].map(([val, label]) => (
          <button
            key={val}
            className={`adm-filter-btn ${filter === val ? 'active' : ''}`}
            onClick={() => setFilter(val)}
          >
            {label}
            <span className="adm-filter-count">
              {val === 'all' ? exercises.length
               : val === 'published' ? exercises.filter(e => e.is_published).length
               : exercises.filter(e => !e.is_published).length}
            </span>
          </button>
        ))}
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="adm-empty">
          <p>Aucun exercice trouvé.</p>
          <button className="adm-btn adm-btn-create" onClick={() => navigate('/admin/exercises/create')}>
            Créer le premier exercice
          </button>
        </div>
      ) : (
        <div className="adm-table-wrapper">
          <table className="adm-table">
            <thead>
              <tr>
                <th>Titre</th>
                <th>Difficulté</th>
                <th>Langage</th>
                <th>Tests</th>
                <th>Statut</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(ex => (
                <tr key={ex.id}>
                  <td className="adm-td-title">{ex.title}</td>
                  <td>
                    <span className={`adm-badge difficulty-${ex.difficulty}`}>
                      {difficultyLabel[ex.difficulty]}
                    </span>
                  </td>
                  <td>
                    <span className="adm-badge lang">{ex.language}</span>
                  </td>
                  <td className="adm-td-center">{ex.test_cases_count ?? '—'}</td>
                  <td>
                    <span className={`adm-status ${ex.is_published ? 'published' : 'draft'}`}>
                      {ex.is_published ? '● Publié' : '○ Brouillon'}
                    </span>
                  </td>
                  <td className="adm-td-actions">
                    <button
                      className="adm-action-btn edit"
                      onClick={() => navigate(`/admin/exercises/${ex.id}/edit`)}
                    >✏️</button>
                    <button
                      className={`adm-action-btn ${ex.is_published ? 'unpublish' : 'publish'}`}
                      onClick={() => handlePublish(ex.id, ex.is_published)}
                      title={ex.is_published ? 'Dépublier' : 'Publier'}
                    >
                      {ex.is_published ? '🔒' : '🚀'}
                    </button>
                    <button
                      className="adm-action-btn delete"
                      onClick={() => handleDelete(ex.id, ex.title)}
                    >🗑️</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
