import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { generateAIExercise, pollAIGeneration } from '../../services/api';
import ExerciseForm from './ExerciseForm';
import toast from 'react-hot-toast';
import './GenerateAI.css';

const POLL_INTERVAL = 3000;

const GenerateAI = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState('config');
  const [generating, setGenerating] = useState(false);
  const [prefill, setPrefill] = useState(null);
  const [requestId, setRequestId] = useState(null);
  const [statusMsg, setStatusMsg] = useState('');
  const pollRef = useRef(null);

  const [config, setConfig] = useState({
    provider: 'ollama',
    model: 'qwen2.5-coder:7b',
    difficulty: 'facile',
    language: 'python',
    topic: '',
    extra_instructions: '',
    auto_publish: false,
    temperature: 0.7,
  });

  const handleProviderChange = (provider) => {
    const defaultModel = provider === 'ollama' ? 'qwen2.5-coder:7b' : 'gemini-1.5-flash';
    setConfig(c => ({ ...c, provider, model: defaultModel }));
  };

  useEffect(() => {
    if (!requestId) return;
    const poll = async () => {
      try {
        const res = await pollAIGeneration(requestId);
        const data = res.data;
        if (data.status === 'completed') {
          clearInterval(pollRef.current);
          setGenerating(false);
          toast.success('Exercice généré ! Vérifie et ajuste avant de publier.');
          setPrefill({ exercise_id: data.exercise_id, title: data.exercise_title, validation_score: data.validation_score, attempts: data.attempts });
          setStep('preview');
        } else if (data.status === 'failed') {
          clearInterval(pollRef.current);
          setGenerating(false);
          setStep('config');
          toast.error(data.error_message || 'La génération IA a échoué.');
        } else {
          setStatusMsg(data.status === 'running' ? `Génération en cours… (tentative ${data.attempts || 1})` : "En file d'attente…");
        }
      } catch {
        clearInterval(pollRef.current);
        setGenerating(false);
        setStep('config');
        toast.error('Erreur lors du suivi de la génération.');
      }
    };
    pollRef.current = setInterval(poll, POLL_INTERVAL);
    poll();
    return () => clearInterval(pollRef.current);
  }, [requestId]);

  const handleGenerate = async () => {
    if (!config.topic.trim()) { toast.error("Merci d'indiquer un thème."); return; }
    setGenerating(true);
    setStatusMsg("Envoi de la demande…");
    setStep('waiting');
    try {
      const res = await generateAIExercise(config);
      setRequestId(res.data.id);
    } catch (err) {
      setGenerating(false);
      setStep('config');
      toast.error(err.response?.data?.detail || 'Erreur lors du lancement de la génération.');
    }
  };

  if (step === 'preview') return <ExerciseForm prefill={prefill} />;

  if (step === 'waiting') {
    return (
      <div className="gen-container">
        <div className="gen-card" style={{ textAlign: 'center' }}>
          <div className="gen-icon">🤖</div>
          <h2 className="gen-title">Génération en cours…</h2>
          <p className="gen-subtitle">{statusMsg}</p>
          <span className="gen-spinner" style={{ display: 'inline-block', margin: '1rem auto' }} />
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginTop: '1rem' }}>
            {config.provider === 'ollama'
              ? 'Ollama (local) peut prendre 30–90 secondes selon ta machine.'
              : 'Cela peut prendre 20–60 secondes.'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="gen-container">
      <div className="gen-card">
        <button className="gen-back" onClick={() => navigate('/admin')}>← Retour</button>
        <div className="gen-icon">🤖</div>
        <h1 className="gen-title">Générer un exercice via IA</h1>
        <p className="gen-subtitle">
          L'IA créera automatiquement un exercice avec énoncé, solution de référence et tests.
          Vous pourrez tout modifier avant de publier.
        </p>
        <div className="gen-form">

          <div className="gen-field">
            <label>Modèle IA</label>
            <select className="gen-select" value={config.provider} onChange={e => handleProviderChange(e.target.value)}>
              <option value="ollama">Ollama — qwen2.5-coder:7b (local)</option>
              <option value="gemini">Google Gemini</option>
            </select>
          </div>

          {config.provider === 'gemini' && (
            <div className="gen-field">
              <label>Version Gemini</label>
              <select className="gen-select" value={config.model} onChange={e => setConfig(c => ({ ...c, model: e.target.value }))}>
                <option value="gemini-3.5-flash">gemini-3.5-flash (rapide)</option>
                <option value="gemini-3.5-pro">gemini-3.5-pro (qualité)</option>
              </select>
            </div>
          )}

          <div className="gen-field">
            <label>Thème / Sujet <span className="gen-required">*</span></label>
            <input className="gen-input" value={config.topic} onChange={e => setConfig(c => ({ ...c, topic: e.target.value }))} placeholder="ex : manipulation de chaînes, récursivité, tri par sélection…" />
          </div>

          <div className="gen-row">
            <div className="gen-field">
              <label>Difficulté</label>
              <select className="gen-select" value={config.difficulty} onChange={e => setConfig(c => ({ ...c, difficulty: e.target.value }))}>
                <option value="facile">Facile</option>
                <option value="moyen">Moyen</option>
                <option value="difficile">Difficile</option>
              </select>
            </div>
            <div className="gen-field">
              <label>Langage</label>
              <select className="gen-select" value={config.language} onChange={e => setConfig(c => ({ ...c, language: e.target.value }))}>
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="java">Java</option>
              </select>
            </div>
          </div>

          <div className="gen-field">
            <label>Instructions supplémentaires <span className="gen-optional">(optionnel)</span></label>
            <input className="gen-input" value={config.extra_instructions} onChange={e => setConfig(c => ({ ...c, extra_instructions: e.target.value }))} placeholder="ex : utilise uniquement des listes, évite la récursivité…" />
          </div>

          <div className="gen-row" style={{ alignItems: 'center' }}>
            <div className="gen-field">
              <label>Créativité : {config.temperature}</label>
              <input type="range" min="0" max="1" step="0.1" value={config.temperature} onChange={e => setConfig(c => ({ ...c, temperature: parseFloat(e.target.value) }))} style={{ width: '100%' }} />
            </div>
            <div className="gen-field" style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 20 }}>
              <input type="checkbox" id="auto-publish" checked={config.auto_publish} onChange={e => setConfig(c => ({ ...c, auto_publish: e.target.checked }))} />
              <label htmlFor="auto-publish" style={{ cursor: 'pointer', marginBottom: 0 }}>Publier automatiquement</label>
            </div>
          </div>

          <button className="gen-btn" onClick={handleGenerate} disabled={generating}>
            {generating ? <><span className="gen-spinner" /> Génération en cours…</> : "✨ Générer l'exercice"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default GenerateAI;
