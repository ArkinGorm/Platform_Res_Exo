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

// Authentification
export const login = (email, password) => 
  API.post('/auth/login/', { email, password });

export const register = (userData) => 
  API.post('/auth/register/', userData);

export const getProfile = () => 
  API.get('/auth/users/me/');

// Exercices
export const getExercises = () => 
  API.get('/exercises/published/');

export const getExercise = (id) => 
  API.get(`/exercises/${id}/`);

// Soumissions
export const submitSolution = (exerciseId, code) => 
  API.post('/submissions/submit/', { 
    exercise: exerciseId, 
    code 
  });

export const getSubmissionStatus = (submissionId) => 
  API.get(`/submissions/${submissionId}/`);

export const getMyStats = () => 
  API.get('/submissions/my-stats/');

export default API;