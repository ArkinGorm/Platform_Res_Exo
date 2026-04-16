import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import CodeMirror from '@uiw/react-codemirror';
import { javascript } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import { getExercise, submitSolution, getSubmissionStatus, runCode } from '../../services/api';
import toast from 'react-hot-toast';
import './ExerciseDetail.css';

const ExerciseDetail = () => {
  const { id } = useParams();
  const [exercise, setExercise] = useState(null);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [submissionId, setSubmissionId] = useState(null);
  const [globalStatus, setGlobalStatus] = useState(null);
  const [consoleLogs, setConsoleLogs] = useState([]);
  const [userInput, setUserInput] = useState('');
  const consoleRef = useRef(null);

  useEffect(() => { loadExercise(); }, [id]);

  useEffect(() => {
    let interval;
    if (submissionId) interval = setInterval(checkSubmission, 2000);
    return () => clearInterval(interval);
  }, [submissionId]);

  useEffect(() => {
    if (consoleRef.current)
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
  }, [consoleLogs]);

  const addLog = (text, type = 'info') =>
    setConsoleLogs(prev => [...prev, { text, type }]);

  const loadExercise = async () => {
    try {
      const response = await getExercise(id);
      setExercise(response.data);
      if (response.data.language === 'javascript')
        setCode('// Écris ton code ici\n');
      else if (response.data.language === 'python')
        setCode('# Écris ton code ici\n');
    } catch {
      toast.error("Erreur lors du chargement de l'exercice");
    } finally {
      setLoading(false);
    }
  };

  /* ── EXÉCUTER : entrée libre, pas de sauvegarde ── */
  const handleRun = async () => {
    setRunning(true);
    setConsoleLogs([]);
    addLog(`▶ Exécution${userInput ? ` avec entrée : ${userInput}` : ''}`, 'info');

    try {
      const response = await runCode(id, code, userInput);
      const { output, error } = response.data;

      if (output) addLog(output, 'stdout');
      if (error) addLog(error, 'error');
      if (!output && !error) addLog('(aucune sortie)', 'info');
    } catch {
      addLog('Erreur lors de l\'exécution', 'error');
      toast.error('Erreur lors de l\'exécution');
    } finally {
      setRunning(false);
    }
  };

  /* ── SOUMETTRE : tests officiels, sauvegarde en base ── */
  const handleSubmit = async () => {
    setSubmitting(true);
    setResults(null);
    setGlobalStatus(null);
    setConsoleLogs([]);
    addLog('⇪ Soumission en cours...', 'info');

    try {
      const response = await submitSolution(id, code);
      setSubmissionId(response.data.submission_id);
      addLog(`Tâche reçue [#${response.data.submission_id}]`, 'info');
      addLog('Exécution des tests officiels...', 'info');
    } catch {
      addLog('Erreur lors de la soumission', 'error');
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
        setGlobalStatus(submission.status);

        submission.test_results?.forEach((result, index) => {
          if (result.output) addLog(`[Test ${index + 1}] stdout: ${result.output}`, 'stdout');
          if (result.error_message) addLog(`[Test ${index + 1}] stderr: ${result.error_message}`, 'error');
        });

        if (submission.status === 'passed') {
          addLog('✓ Tous les tests sont passés !', 'success');
          toast.success('Bravo ! Tous les tests sont passés !');
        } else {
          addLog('✗ Certains tests ont échoué', 'error');
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

  const passedCount = results?.filter(r => r.passed).length ?? 0;
  const totalCount = results?.length ?? 0;
  const successRate = totalCount > 0 ? Math.round((passedCount / totalCount) * 100) : 0;
  const isBusy = submitting || running;

  if (loading) return <div className="ex-loading">Chargement...</div>;
  if (!exercise) return (
    <div className="ex-error">
      <h2>Exercice introuvable</h2>
      <p>Impossible de charger cet exercice.</p>
      <button onClick={() => window.location.reload()}>Réessayer</button>
    </div>
  );

  return (
    <div className="ex-container">

      {/* ── Ligne du haut ── */}
      <div className="ex-top">

        {/* Énoncé */}
        <div className="ex-panel ex-enonce">
          <div className="ex-panel-header">
            <span className="ex-panel-title">Énoncé</span>
            <div className="ex-badges">
              <span className={`ex-badge difficulty-${exercise.difficulty}`}>{exercise.difficulty}</span>
              <span className="ex-badge lang">{exercise.language}</span>
            </div>
          </div>
          <div className="ex-panel-body">
            <p className="ex-description">{exercise.description}</p>
          </div>
        </div>

        {/* Éditeur */}
        <div className="ex-panel ex-editor">
          <div className="ex-panel-header">
            <span className="ex-panel-title">Code</span>
          </div>
          <div className="ex-editor-body">
            <CodeMirror
              value={code}
              onChange={(value) => setCode(value)}
              height="100%"
              extensions={getLanguageExtension()}
              theme="dark"
              style={{ height: '100%' }}
            />
          </div>
        </div>

      </div>

      {/* ── Ligne du bas ── */}
      <div className="ex-bottom">

        {/* Résultats */}
        <div className="ex-panel ex-results">
          <div className="ex-panel-header">
            <span className="ex-panel-title">Résultat</span>
            {globalStatus && <span className={`ex-status-dot ${globalStatus}`} />}
          </div>
          <div className="ex-panel-body ex-results-body">
            <div className="ex-stat">
              <span className="ex-stat-label">Test :</span>
              <span className="ex-stat-value">{passedCount}/{totalCount}</span>
            </div>
            <div className="ex-stat">
              <span className="ex-stat-label">% de Réussite :</span>
              <span className={`ex-stat-value rate-${successRate === 100 ? 'full' : successRate > 0 ? 'partial' : 'zero'}`}>
                {successRate}%
              </span>
            </div>

            {results && (
              <div className="ex-test-list">
                {results.map((result, index) => (
                  <div key={index} className={`ex-test-item ${result.passed ? 'passed' : 'failed'}`}>
                    <span className="ex-test-icon">{result.passed ? '✓' : '✗'}</span>
                    <span className="ex-test-label">Test {index + 1}</span>
                    {result.execution_time != null && (
                      <span className="ex-test-time">{Number(result.execution_time).toFixed(0)}ms</span>
                    )}
                  </div>
                ))}
              </div>
            )}

            {isBusy && (
              <div className="ex-running">
                <span className="ex-spinner" />
                {running ? 'Exécution...' : 'Tests en cours...'}
              </div>
            )}
          </div>
        </div>

        {/* Console */}
        <div className="ex-panel ex-console">
          <div className="ex-panel-header">
            <span className="ex-panel-title">Console</span>
            {consoleLogs.length > 0 && (
              <button className="ex-clear-btn" onClick={() => setConsoleLogs([])}>✕</button>
            )}
          </div>

          {/* Zone saisie entrée libre — toujours visible */}
          <div className="ex-input-zone">
            <input
              className="ex-input-field"
              type="text"
              placeholder='Entrée optionnelle — ex: [2, 3] ou "hello"'
              value={userInput}
              onChange={e => setUserInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !isBusy && handleRun()}
            />
            <span className="ex-input-hint">↵ pour exécuter</span>
          </div>

          <div className="ex-console-body" ref={consoleRef}>
            {consoleLogs.length === 0 && (
              <span className="ex-console-placeholder">
                La sortie de ton code apparaîtra ici...
              </span>
            )}
            {consoleLogs.map((log, i) => (
              <div key={i} className={`ex-log ex-log-${log.type}`}>
                <span className="ex-log-text">{log.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="ex-panel ex-actions">
          <div className="ex-panel-header">
            <span className="ex-panel-title">Actions</span>
          </div>
          <div className="ex-panel-body ex-actions-body">
            <button
              className="ex-btn ex-btn-run"
              onClick={handleRun}
              disabled={isBusy}
            >
              <span className="ex-btn-icon">▶</span>
              Exécuter
            </button>

            <button
              className="ex-btn ex-btn-submit"
              onClick={handleSubmit}
              disabled={isBusy}
            >
              <span className="ex-btn-icon">⇪</span>
              Soumettre
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};

export default ExerciseDetail;
