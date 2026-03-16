import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import CodeMirror from '@uiw/react-codemirror';
import { javascript } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import { getExercise, submitSolution, getSubmissionStatus } from '../../services/api';
import toast from 'react-hot-toast';
import './ExerciseDetail.css';

const ExerciseDetail = () => {
  const { id } = useParams();
  const [exercise, setExercise] = useState(null);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [results, setResults] = useState(null);
  const [submissionId, setSubmissionId] = useState(null);

  useEffect(() => {
    loadExercise();
  }, [id]);

  useEffect(() => {
    let interval;
    if (submissionId) {
      interval = setInterval(checkSubmission, 2000);
    }
    return () => clearInterval(interval);
  }, [submissionId]);

  const loadExercise = async () => {
    try {
      const response = await getExercise(id);
      setExercise(response.data);
      // Template de base selon le langage
      if (response.data.language === 'javascript') {
        setCode('function solution(a, b) {\n  // Votre code ici\n  \n}');
      } else if (response.data.language === 'python') {
        setCode('def solution(a, b):\n    # Votre code ici\n    pass');
      }
    } catch (error) {
      toast.error('Erreur lors du chargement de l\'exercice');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setResults(null);
    
    try {
      const response = await submitSolution(id, code);
      setSubmissionId(response.data.submission_id);
      toast.success('Code envoyé ! En attente des résultats...');
    } catch (error) {
      toast.error('Erreur lors de la soumission');
      setSubmitting(false);
    }
  };

  const checkSubmission = async () => {
    try {
      const response = await getSubmissionStatus(submissionId);
      const submission = response.data;
      
      if (submission.status !== 'pending') {
        clearInterval();
        setResults(submission.test_results);
        setSubmitting(false);
        setSubmissionId(null);
        
        if (submission.status === 'passed') {
          toast.success('Bravo ! Tous les tests sont passés !');
        } else {
          toast.error('Certains tests ont échoué');
        }
      }
    } catch (error) {
      console.error('Erreur vérification:', error);
    }
  };

  const getLanguageExtension = () => {
    switch (exercise?.language) {
      case 'javascript': return [javascript()];
      case 'python': return [python()];
      default: return [];
    }
  };

  if (loading) {
    return <div className="loading">Chargement...</div>;
  }

  return (
    <div className="exercise-detail-container">
      <div className="exercise-info">
        <h1>{exercise.title}</h1>
        <div className="exercise-meta">
          <span className={`difficulty ${exercise.difficulty}`}>
            {exercise.difficulty}
          </span>
          <span className="language">{exercise.language}</span>
        </div>
        <div className="description">
          <h3>Énoncé :</h3>
          <p>{exercise.description}</p>
        </div>
      </div>

      <div className="code-section">
        <div className="editor-container">
          <CodeMirror
            value={code}
            onChange={(value) => setCode(value)}
            height="400px"
            extensions={getLanguageExtension()}
            theme="dark"
          />
        </div>

        <button 
          onClick={handleSubmit}
          disabled={submitting}
          className="submit-btn"
        >
          {submitting ? 'Exécution...' : 'Soumettre'}
        </button>

        {results && (
          <div className="results">
            <h3>Résultats des tests :</h3>
            {results.map((result, index) => (
              <div key={index} className={`test-result ${result.passed ? 'passed' : 'failed'}`}>
                <div className="test-header">
                  <span className="test-icon">
                    {result.passed ? 'Exellent ✅' : 'OH Mince! ❌'}
                  </span>
                  <span className="test-name">Test {index + 1}</span>
                </div>
                <div className="test-details">
                  <p><strong>Entrée:</strong> {result.input}</p>
                  <p><strong>Attendu:</strong> {result.expected}</p>
                  <p><strong>Obtenu:</strong> {result.actual_output || result.error}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ExerciseDetail;