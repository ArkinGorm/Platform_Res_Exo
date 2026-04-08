import axios from 'axios';
import toast from 'react-hot-toast';

const API = axios.create({
  baseURL: 'http://localhost:8000/api'
});

// Intercepteur pour ajouter le token à chaque requête
API.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Intercepteur pour gérer les erreurs
API.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
      toast.error('Session expirée, veuillez vous reconnecter');
    } else if (error.response?.status === 403) {
      toast.error('Accès non autorisé');
    } else if (error.response?.status === 404) {
      toast.error('Ressource non trouvée');
    } else if (error.response?.status >= 500) {
      toast.error('Erreur serveur, réessayez plus tard');
    }
    return Promise.reject(error);
  }
);

// ── Authentification ──────────────────────────────────────────────────────────

export const login = (email, password) =>
  API.post('/auth/login/', { email, password });

export const register = (userData) =>
  API.post('/auth/register/', userData);

// Retourne directement l'objet user (id, username, email, role)
export const getProfile = () =>
  API.get('/auth/users/me/');

// ── Exercices ─────────────────────────────────────────────────────────────────

export const getExercises = () =>
  API.get('/exercises/published/');

export const getExercise = (id) =>
  API.get(`/exercises/${id}/`);

// ── Soumissions ───────────────────────────────────────────────────────────────

export const submitSolution = (exerciseId, code) =>
  API.post('/submissions/submit/', { exercise: exerciseId, code });

export const getSubmissionStatus = (submissionId) =>
  API.get(`/submissions/${submissionId}/`);

export const getMyStats = () =>
  API.get('/submissions/my-stats/');

export const runCode = (exerciseId, code, userInput) =>
  API.post('/submissions/run/', { exercise_id: exerciseId, code, user_input: userInput });

// ── Admin — Exercices ─────────────────────────────────────────────────────────

export const getAdminExercises = () =>
  API.get('/exercises/?ordering=-created_at');

export const createExercise = (data) =>
  API.post('/exercises/', data);

export const updateExercise = (id, data) =>
  API.put(`/exercises/${id}/`, data);

export const deleteExercise = (id) =>
  API.delete(`/exercises/${id}/`);

export const publishExercise = (id) =>
  API.post(`/exercises/${id}/publish/`);

export const unpublishExercise = (id) =>
  API.post(`/exercises/${id}/unpublish/`);

export const testExercise = (id, code) =>
  API.post(`/exercises/${id}/test_exercise/`, { code });

export const addTestCase = (exerciseId, data) =>
  API.post(`/exercises/${exerciseId}/test_cases/`, data);

export const deleteTestCase = (exerciseId, tcId) =>
  API.delete(`/exercises/${exerciseId}/test_cases/${tcId}/`);

// ── Génération IA ─────────────────────────────────────────────────────────────
// L'URL correcte est /exercises/ai/generate/ (préfixe "ai/" ajouté dans exercises/urls.py)

export const generateAIExercise = (config) =>
  API.post('/exercises/ai/generate/', config);

export const pollAIGeneration = (id) =>
  API.get(`/exercises/ai/generate/${id}/`);

export const cancelAIGeneration = (id) =>
  API.delete(`/exercises/ai/generate/${id}/`);

export const getAIProviders = () =>
  API.get('/exercises/ai/generate/providers/');

export const getAIHistory = () =>
  API.get('/exercises/ai/generate/history/');

// ── Validation des test cases ─────────────────────────────────────────────────

export const validateTests = (data) =>
  API.post('/exercises/validate_tests/', data);

export default API;
