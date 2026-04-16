import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import CodeMirror from '@uiw/react-codemirror';
import { javascript } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import {
  createExercise, updateExercise, getExercise,
  testExercise, validateTests,
} from '../../services/api';
import toast from 'react-hot-toast';
import './ExerciseForm.css';

const EMPTY_TC = { input_data: '', expected_output: '', description: '', order: 1 };

const ExerciseForm = ({ prefill = null }) => {
  const { id }   = useParams();
  const navigate = useNavigate();
  const isEdit   = Boolean(id);

  const [form, setForm] = useState({
    title: '', description: '', difficulty: 'facile',
    language: 'python', solution: '', solution_template: '', is_published: false,
  });
  const [testCases, setTestCases]       = useState([{ ...EMPTY_TC }]);
  const [testResults, setTestResults]   = useState(null);
  const [validation, setValidation]     = useState(null);
  const [saving, setSaving]             = useState(false);
  const [testing, setTesting]           = useState(false);
  const [validating, setValidating]     = useState(false);
  const [activeTab, setActiveTab]       = useState('info');
  // Pour les exercices IA : afficher solution complète ou template étudiant
  const [showSolutionTemplate, setShowSolutionTemplate] = useState(false);

  useEffect(() => {
    if (prefill) {
      setForm({
        title:             prefill.title             || '',
        description:       prefill.description       || '',
        difficulty:        prefill.difficulty        || 'facile',
        language:          prefill.language          || 'python',
        solution:          prefill.solution          || '',
        solution_template: prefill.solution_template || prefill.solution || '',
        is_published:      false,
      });
      if (prefill.test_cases?.length > 0) {
        setTestCases(prefill.test_cases.map((tc, i) => ({ ...tc, order: i + 1 })));
      }
      // Basculer sur l'onglet solution pour vérifier ce que l'IA a généré
      setActiveTab('solution');
    } else if (isEdit) {
      loadExercise();
    }
  }, [prefill, id]);

  const loadExercise = async () => {
    try {
      const res = await getExercise(id);
      const ex  = res.data;
      setForm({
        title:             ex.title,
        description:       ex.description,
        difficulty:        ex.difficulty,
        language:          ex.language,
        solution:          ex.solution          || '',
        solution_template: ex.solution_template || ex.solution || '',
        is_published:      ex.is_published,
      });
      if (ex.test_cases?.length > 0) setTestCases(ex.test_cases);
    } catch { toast.error('Erreur lors du chargement'); }
  };

  const handleField  = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const handleTc     = (i, k, v) =>
    setTestCases(prev => prev.map((tc, idx) => idx === i ? { ...tc, [k]: v } : tc));
  const addTc        = () => setTestCases(p => [...p, { ...EMPTY_TC, order: p.length + 1 }]);
  const removeTc     = (i) => {
    if (testCases.length === 1) return toast.error('Il faut au moins un test case');
    setTestCases(p => p.filter((_, idx) => idx !== i));
  };

  // Valeur courante de l'éditeur selon le toggle solution/template
  const currentSolutionValue = showSolutionTemplate
    ? form.solution_template
    : form.solution;

  const handleSolutionEditorChange = (v) => {
    if (showSolutionTemplate) {
      handleField('solution_template', v);
    } else {
      handleField('solution', v);
    }
  };

  // ── Tester la solution ───────────────────────────────────────
  const handleTest = async () => {
    if (!form.solution.trim()) return toast.error('Écris une solution de référence d\'abord');
    setTesting(true); setTestResults(null);
    try {
      let eid = id;
      if (!eid) {
        const res = await createExercise({ ...form, test_cases: testCases });
        eid = res.data.id;
      }
      const res = await testExercise(eid, form.solution);
      setTestResults(res.data);
      res.data.all_passed
        ? toast.success('Tous les tests passent ✓')
        : toast.error(`${res.data.passed}/${res.data.total} tests passent`);
    } catch (e) {
      toast.error(e.response?.data?.error || 'Erreur lors du test');
    } finally { setTesting(false); }
  };

  // ── Valider les test cases ───────────────────────────────────
  const handleValidate = async () => {
    setValidating(true); setValidation(null);
    try {
      const res = await validateTests({
        language:    form.language,
        solution:    form.solution,
        test_cases:  testCases,
        description: form.description,
        title:       form.title,
      });
      const report = res.data;
      setValidation(report);
      setActiveTab('validate');

      if (report.test_cases?.length > 0) {
        setTestCases(prev => prev.map((tc, i) => {
          const checked = report.test_cases[i];
          if (checked?.status === 'mismatch' && checked.suggested_output !== undefined) {
            return { ...tc, expected_output: checked.suggested_output };
          }
          return tc;
        }));
      }

      if (report.issues.length === 0) toast.success('Validation réussie !');
      else toast.error(`${report.issues.length} problème(s) détecté(s)`);
    } catch (e) {
      toast.error(e.response?.data?.error || 'Erreur lors de la validation');
    } finally { setValidating(false); }
  };

  // ── Sauvegarder / Publier ────────────────────────────────────
  const handleSave = async (publish = false) => {
    if (!form.title.trim()) return toast.error('Le titre est requis');
    if (testCases.some(tc => !tc.input_data.trim() || !tc.expected_output.trim()))
      return toast.error('Tous les test cases doivent avoir une entrée et une sortie attendue');
    if (publish && validation?.issues?.length > 0)
      return toast.error('Règle les problèmes de validation avant de publier');

    setSaving(true);
    try {
      const payload = { ...form, is_published: publish, test_cases: testCases };
      if (isEdit) {
        await updateExercise(id, payload);
        toast.success(publish ? 'Exercice publié !' : 'Exercice mis à jour');
      } else {
        await createExercise(payload);
        toast.success(publish ? 'Exercice créé et publié !' : 'Exercice sauvegardé en brouillon');
      }
      navigate('/admin');
    } catch (e) {
      toast.error(e.response?.data?.error || 'Erreur lors de la sauvegarde');
    } finally { setSaving(false); }
  };

  const getLangExt = () => {
    if (form.language === 'javascript') return [javascript()];
    if (form.language === 'python')     return [python()];
    return [];
  };

  const hasBlockers = validation?.issues?.length > 0;
  const hasSolutionTemplate = Boolean(form.solution_template && form.solution_template !== form.solution);

  return (
    <div className="ef-container">

      {/* ── Header ── */}
      <div className="ef-header">
        <button className="ef-back-btn" onClick={() => navigate('/admin')}>← Retour</button>
        <h1 className="ef-title">
          {prefill ? '✨ Exercice généré par IA' : isEdit ? 'Modifier l\'exercice' : 'Nouvel exercice'}
        </h1>
        <div className="ef-header-actions">
          <button className="ef-btn ef-btn-validate" onClick={handleValidate} disabled={validating || saving}>
            {validating ? '⏳...' : '🔍 Valider'}
          </button>
          <button className="ef-btn ef-btn-test" onClick={handleTest} disabled={testing || saving}>
            {testing ? '⏳...' : '▶ Tester'}
          </button>
          <button className="ef-btn ef-btn-draft" onClick={() => handleSave(false)} disabled={saving}>
            💾 Brouillon
          </button>
          <button
            className="ef-btn ef-btn-publish"
            onClick={() => handleSave(true)}
            disabled={saving || hasBlockers}
            title={hasBlockers ? 'Règle les problèmes de validation d\'abord' : ''}
          >
             Publier
          </button>
        </div>
      </div>

      {/* ── Bandeau IA ── */}
      {prefill && (
        <div className="ef-ai-banner">
          🤖 Exercice généré par IA
          {prefill.validation_score && (
            <span className="ef-ai-score"> · Score qualité : {prefill.validation_score}/100</span>
          )}
          {prefill.attempts && (
            <span className="ef-ai-attempts"> · {prefill.attempts} tentative(s)</span>
          )}
          <span className="ef-ai-hint"> — Vérifiez et ajustez avant de publier.</span>
        </div>
      )}

      {/* ── Onglets ── */}
      <div className="ef-tabs">
        {[
          ['info',     '📋 Informations'],
          ['solution', '💻 Solution'],
          ['tests',    `🧪 Tests (${testCases.length})`],
          ['validate', `🔍 Validation${validation ? (hasBlockers ? ' ⚠' : ' ✓') : ''}`],
        ].map(([tab, label]) => (
          <button
            key={tab}
            className={`ef-tab ${activeTab === tab ? 'active' : ''} ${
              tab === 'validate' && validation
                ? hasBlockers ? 'tab-warn' : 'tab-ok'
                : ''
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="ef-body">

        {/* ── Onglet Informations ── */}
        {activeTab === 'info' && (
          <div className="ef-section">
            <div className="ef-field">
              <label>Titre *</label>
              <input className="ef-input" value={form.title}
                onChange={e => handleField('title', e.target.value)}
                placeholder="Ex: Somme de deux nombres" />
            </div>
            <div className="ef-field">
              <label>Description / Énoncé *</label>
              <textarea className="ef-textarea" value={form.description} rows={6}
                onChange={e => handleField('description', e.target.value)}
                placeholder={
                  `Décris clairement :\n` +
                  `- Ce que la fonction solution() doit faire\n` +
                  `- Les paramètres qu'elle reçoit\n` +
                  `- Ce qu'elle doit retourner\n` +
                  `- Le langage utilisé`
                } />
            </div>
            <div className="ef-row">
              <div className="ef-field">
                <label>Difficulté</label>
                <select className="ef-select" value={form.difficulty}
                  onChange={e => handleField('difficulty', e.target.value)}>
                  <option value="facile">Facile</option>
                  <option value="moyen">Moyen</option>
                  <option value="difficile">Difficile</option>
                </select>
              </div>
              <div className="ef-field">
                <label>Langage</label>
                <select className="ef-select" value={form.language}
                  onChange={e => handleField('language', e.target.value)}>
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                </select>
              </div>
            </div>
            {validation?.warnings?.filter(w =>
              w.includes('énoncé') || w.includes('titre') || w.includes('fonction') || w.includes('paramètre')
            ).map((w, i) => (
              <div key={i} className="ef-clarity-hint">💡 {w}</div>
            ))}
          </div>
        )}

        {/* ── Onglet Solution ── */}
        {activeTab === 'solution' && (
          <div className="ef-section">

            {/* Toggle solution complète / template étudiant (uniquement si exercice IA) */}
            {hasSolutionTemplate && (
              <div className="ef-solution-toggle">
                <button
                  className={`ef-toggle-btn ${!showSolutionTemplate ? 'active' : ''}`}
                  onClick={() => setShowSolutionTemplate(false)}
                >
                  🔑 Solution de référence
                </button>
                <button
                  className={`ef-toggle-btn ${showSolutionTemplate ? 'active' : ''}`}
                  onClick={() => setShowSolutionTemplate(true)}
                >
                  📝 Template étudiant
                </button>
              </div>
            )}

            <div className="ef-hint">
              {showSolutionTemplate
                ? "Template affiché à l'étudiant — il doit compléter les TODO."
                : "Solution complète de référence — sert à vérifier les tests. Non visible par les participants."
              }
            </div>

            <div className="ef-editor-wrapper">
              <CodeMirror
                value={currentSolutionValue}
                onChange={handleSolutionEditorChange}
                height="380px"
                extensions={getLangExt()}
                theme="dark"
              />
            </div>

            {testResults && (
              <div className="ef-test-results">
                <div className={`ef-test-summary ${testResults.all_passed ? 'passed' : 'failed'}`}>
                  {testResults.all_passed ? '✓' : '✗'} {testResults.passed}/{testResults.total} tests passent
                </div>
                {testResults.results.map((r, i) => (
                  <div key={i} className={`ef-test-row ${r.passed ? 'passed' : 'failed'}`}>
                    <span>{r.passed ? '✓' : '✗'} Test {i + 1}</span>
                    <span className="ef-test-output">
                      Obtenu : <code>{r.output || r.error || '(vide)'}</code>
                    </span>
                    <span className="ef-test-time">{Number(r.execution_time).toFixed(0)}ms</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Onglet Tests ── */}
        {activeTab === 'tests' && (
          <div className="ef-section">
            <div className="ef-hint">
              <code>input_data</code> doit être évaluable directement —
              ex: <code>[1, 2]</code>, <code>"hello"</code>, <code>42</code>.<br/>
              <code>expected_output</code> doit être la représentation string du retour de <code>solution()</code>.
            </div>
            {testCases.map((tc, index) => {
              const tcReport = validation?.test_cases?.[index];
              return (
                <div key={index} className={`ef-tc-card ${
                  tcReport?.status === 'mismatch' ? 'tc-mismatch'
                  : tcReport?.status === 'error'   ? 'tc-error'
                  : tcReport?.status === 'ok'       ? 'tc-ok'
                  : ''
                }`}>
                  <div className="ef-tc-header">
                    <span className="ef-tc-num">Test {index + 1}</span>
                    {tcReport && (
                      <span className={`ef-tc-status ${tcReport.status}`}>
                        {tcReport.status === 'ok'       ? '✓ OK'
                         : tcReport.status === 'mismatch' ? '⚠ Corrigé auto'
                         : tcReport.status === 'error'    ? '✗ Erreur'
                         : '—'}
                      </span>
                    )}
                    <button className="ef-tc-remove" onClick={() => removeTc(index)}>✕</button>
                  </div>
                  <div className="ef-tc-body">
                    <div className="ef-field">
                      <label>Entrée (input_data)</label>
                      <input className="ef-input mono" value={tc.input_data}
                        onChange={e => handleTc(index, 'input_data', e.target.value)}
                        placeholder="ex: [2, 3]" />
                    </div>
                    <div className="ef-field">
                      <label>Sortie attendue</label>
                      <input className="ef-input mono" value={tc.expected_output}
                        onChange={e => handleTc(index, 'expected_output', e.target.value)}
                        placeholder="ex: 5" />
                      {tcReport?.computed_output && tcReport.status === 'mismatch' && (
                        <span className="ef-tc-computed">
                          Calculé : <code>{tcReport.computed_output}</code> (appliqué auto)
                        </span>
                      )}
                    </div>
                    <div className="ef-field">
                      <label>Description (optionnel)</label>
                      <input className="ef-input" value={tc.description}
                        onChange={e => handleTc(index, 'description', e.target.value)}
                        placeholder="ex: Cas nominal" />
                    </div>
                  </div>
                  {tcReport?.messages?.map((msg, j) => (
                    <div key={j} className="ef-tc-message">{msg}</div>
                  ))}
                </div>
              );
            })}
            <button className="ef-add-tc-btn" onClick={addTc}>+ Ajouter un test case</button>
          </div>
        )}

        {/* ── Onglet Validation ── */}
        {activeTab === 'validate' && (
          <div className="ef-section">
            {!validation ? (
              <div className="ef-validate-empty">
                <p>Clique sur <strong>🔍 Valider</strong> pour analyser tes test cases.</p>
                <p className="ef-muted">La validation vérifie :</p>
                <ul className="ef-validate-checklist">
                  <li>✓ Cohérence des expected_output avec la solution de référence</li>
                  <li>✓ Doublons dans les inputs</li>
                  <li>✓ Tests "passoires" (code trivial qui passe quand même)</li>
                  <li>✓ Clarté de l'énoncé (description, paramètres, retour)</li>
                </ul>
              </div>
            ) : (
              <div className="ef-validate-report">

                <div className={`ef-validate-summary ${validation.can_publish ? 'ok' : 'blocked'}`}>
                  {validation.can_publish
                    ? '✓ Exercice valide — prêt à être publié'
                    : `✗ ${validation.issues.length} problème(s) bloquant(s) à régler`}
                </div>

                {validation.issues.length > 0 && (
                  <div className="ef-validate-block">
                    <h4 className="ef-validate-section-title ef-red">🚫 Problèmes bloquants</h4>
                    {validation.issues.map((issue, i) => (
                      <div key={i} className="ef-validate-item issue">✗ {issue}</div>
                    ))}
                  </div>
                )}

                {validation.auto_fixed.length > 0 && (
                  <div className="ef-validate-block">
                    <h4 className="ef-validate-section-title ef-blue">🔧 Corrections automatiques appliquées</h4>
                    {validation.auto_fixed.map((fix, i) => (
                      <div key={i} className="ef-validate-item fixed">⚡ {fix}</div>
                    ))}
                  </div>
                )}

                {validation.warnings.length > 0 && (
                  <div className="ef-validate-block">
                    <h4 className="ef-validate-section-title ef-orange">⚠ Avertissements</h4>
                    {validation.warnings.map((w, i) => (
                      <div key={i} className="ef-validate-item warning">⚠ {w}</div>
                    ))}
                  </div>
                )}

                {validation.test_cases?.length > 0 && (
                  <div className="ef-validate-block">
                    <h4 className="ef-validate-section-title">📋 Détail par test case</h4>
                    {validation.test_cases.map((tc, i) => (
                      <div key={i} className={`ef-validate-tc ${tc.status}`}>
                        <span className="ef-validate-tc-num">Test {i + 1}</span>
                        <span className="ef-validate-tc-input">
                          input: <code>{tc.input_data}</code>
                        </span>
                        <span className="ef-validate-tc-output">
                          expected: <code>{tc.expected_output}</code>
                        </span>
                        {tc.computed_output && (
                          <span className="ef-validate-tc-computed">
                            calculé: <code>{tc.computed_output}</code>
                          </span>
                        )}
                        <span className={`ef-validate-tc-badge ${tc.status}`}>
                          {tc.status === 'ok'        ? '✓'
                           : tc.status === 'mismatch' ? '⚡ auto-corrigé'
                           : tc.status === 'error'    ? '✗ erreur'
                           : '—'}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                <button className="ef-revalidate-btn" onClick={handleValidate} disabled={validating}>
                  {validating ? '⏳ Validation...' : '↺ Relancer la validation'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ExerciseForm;
