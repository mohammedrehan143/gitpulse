import React, { useState } from 'react';
import {
  Brain,
  Sparkles,
  Send,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Activity,
  Users,
  Flame,
} from 'lucide-react';
import {
  askAIEngineeringAssistant,
  fetchRepositoryAIOverview,
  fetchTeamAIReport,
} from '../services/api';
import {
  AIAssistantChatResponse,
  RepositoryAIOverviewResponse,
  TeamReportResponse,
} from '../types';

interface AIEngineeringAssistantProps {
  currentRepo?: string; // "owner/repo"
  availableRepos?: string[];
}

export const AIEngineeringAssistant: React.FC<AIEngineeringAssistantProps> = ({
  currentRepo,
  availableRepos = [],
}) => {
  const [activeTab, setActiveTab] = useState<'assistant' | 'repo_health' | 'team_report'>('assistant');
  const [targetRepo, setTargetRepo] = useState<string>(currentRepo || (availableRepos[0] || ''));
  const [question, setQuestion] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Results
  const [chatResult, setChatResult] = useState<AIAssistantChatResponse | null>(null);
  const [repoResult, setRepoResult] = useState<RepositoryAIOverviewResponse | null>(null);
  const [teamResult, setTeamResult] = useState<TeamReportResponse | null>(null);

  const presetQuestions = [
    'What happened in my repositories this week?',
    'Which PRs have been open the longest?',
    'Which repositories have been inactive?',
    'Who contributed most recently?',
    'Summarize the latest engineering progress',
  ];

  const handleSendQuestion = async (qToSend?: string) => {
    const query = qToSend || question;
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await askAIEngineeringAssistant(query, targetRepo || undefined);
      setChatResult(res);
      if (!qToSend) setQuestion('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to query assistant');
    } finally {
      setLoading(false);
    }
  };

  const handleFetchRepoHealth = async (forceRefresh = false) => {
    if (!targetRepo || !targetRepo.includes('/')) {
      setError('Please select a valid repository in owner/repo format');
      return;
    }
    const [owner, repo] = targetRepo.split('/');
    setLoading(true);
    setError(null);
    try {
      const res = await fetchRepositoryAIOverview(owner, repo, '30d', forceRefresh);
      setRepoResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch repository health');
    } finally {
      setLoading(false);
    }
  };

  const handleFetchTeamReport = async (forceRefresh = false) => {
    if (!targetRepo || !targetRepo.includes('/')) {
      setError('Please select a valid repository in owner/repo format');
      return;
    }
    const [owner, repo] = targetRepo.split('/');
    setLoading(true);
    setError(null);
    try {
      const res = await fetchTeamAIReport(owner, repo, '7d', forceRefresh);
      setTeamResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch team report');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        backgroundColor: '#121212',
        border: '1px solid #27272a',
        borderRadius: '12px',
        padding: '1.5rem',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.6)',
        color: '#f8fafc',
        marginBottom: '2rem',
      }}
    >
      {/* Header Container */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          paddingBottom: '1.25rem',
          borderBottom: '1px solid #27272a',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 14px rgba(99, 102, 241, 0.4)',
            }}
          >
            <Brain size={22} color="#ffffff" />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0, color: '#ffffff' }}>
                Engineering Intelligence Assistant
              </h2>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  backgroundColor: '#1e1b4b',
                  color: '#a5b4fc',
                  border: '1px solid #4338ca',
                  borderRadius: '20px',
                  padding: '2px 8px',
                }}
              >
                Groq LLM + Strict Grounding
              </span>
            </div>
            <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '4px 0 0 0' }}>
              Natural-language Q&A and velocity insights grounded strictly in database records (zero hallucination).
            </p>
          </div>
        </div>

        {/* Target Repository Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{ fontSize: '12px', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase' }}>
            Context Repo:
          </label>
          <select
            value={targetRepo}
            onChange={(e) => setTargetRepo(e.target.value)}
            style={{
              backgroundColor: '#18181b',
              border: '1px solid #3f3f46',
              color: '#f8fafc',
              fontSize: '13px',
              fontWeight: 500,
              borderRadius: '6px',
              padding: '6px 12px',
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            <option value="">All Monitored Repositories</option>
            {availableRepos.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabs Row */}
      <div
        style={{
          display: 'flex',
          gap: '10px',
          padding: '1rem 0',
          borderBottom: '1px solid #27272a',
          flexWrap: 'wrap',
        }}
      >
        <button
          onClick={() => setActiveTab('assistant')}
          style={{
            padding: '8px 16px',
            fontSize: '13px',
            fontWeight: 600,
            borderRadius: '6px',
            border: activeTab === 'assistant' ? '1px solid #6366f1' : '1px solid #27272a',
            backgroundColor: activeTab === 'assistant' ? '#4f46e5' : '#18181b',
            color: '#ffffff',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease',
          }}
        >
          <Sparkles size={15} />
          Engineering Assistant Q&A
        </button>

        <button
          onClick={() => {
            setActiveTab('repo_health');
            if (!repoResult && targetRepo) handleFetchRepoHealth();
          }}
          style={{
            padding: '8px 16px',
            fontSize: '13px',
            fontWeight: 600,
            borderRadius: '6px',
            border: activeTab === 'repo_health' ? '1px solid #6366f1' : '1px solid #27272a',
            backgroundColor: activeTab === 'repo_health' ? '#4f46e5' : '#18181b',
            color: '#ffffff',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease',
          }}
        >
          <Activity size={15} />
          Repository Health Intelligence
        </button>

        <button
          onClick={() => {
            setActiveTab('team_report');
            if (!teamResult && targetRepo) handleFetchTeamReport();
          }}
          style={{
            padding: '8px 16px',
            fontSize: '13px',
            fontWeight: 600,
            borderRadius: '6px',
            border: activeTab === 'team_report' ? '1px solid #6366f1' : '1px solid #27272a',
            backgroundColor: activeTab === 'team_report' ? '#4f46e5' : '#18181b',
            color: '#ffffff',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease',
          }}
        >
          <Users size={15} />
          Weekly Team Engineering Report
        </button>
      </div>

      {/* Error alert */}
      {error && (
        <div
          style={{
            marginTop: '1rem',
            padding: '10px 14px',
            backgroundColor: '#450a0a',
            border: '1px solid #991b1b',
            borderRadius: '8px',
            color: '#fca5a5',
            fontSize: '13px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={16} />
            {error}
          </span>
          <button
            onClick={() => setError(null)}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              color: '#fca5a5',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 600,
            }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* TAB 1: Natural Language Assistant Q&A */}
      {activeTab === 'assistant' && (
        <div style={{ marginTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Quick preset question chips */}
          <div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: '#a1a1aa',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                display: 'block',
                marginBottom: '8px',
              }}
            >
              Suggested Questions:
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {presetQuestions.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSendQuestion(q)}
                  disabled={loading}
                  style={{
                    fontSize: '12px',
                    fontWeight: 500,
                    backgroundColor: '#18181b',
                    border: '1px solid #3f3f46',
                    color: '#e2e8f0',
                    padding: '6px 14px',
                    borderRadius: '20px',
                    cursor: loading ? 'wait' : 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#27272a';
                    e.currentTarget.style.borderColor = '#6366f1';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = '#18181b';
                    e.currentTarget.style.borderColor = '#3f3f46';
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Input Box and Submit */}
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendQuestion()}
              placeholder="Ask anything about commit velocity, pull requests, inactive repos, or contributors..."
              disabled={loading}
              style={{
                flex: 1,
                backgroundColor: '#09090b',
                border: '1px solid #3f3f46',
                borderRadius: '8px',
                padding: '12px 16px',
                fontSize: '14px',
                color: '#ffffff',
                outline: 'none',
              }}
            />
            <button
              onClick={() => handleSendQuestion()}
              disabled={loading || !question.trim()}
              style={{
                backgroundColor: loading || !question.trim() ? '#27272a' : '#4f46e5',
                color: loading || !question.trim() ? '#71717a' : '#ffffff',
                fontWeight: 600,
                fontSize: '13px',
                padding: '12px 20px',
                borderRadius: '8px',
                border: 'none',
                cursor: loading || !question.trim() ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.15s ease',
                boxShadow: loading || !question.trim() ? 'none' : '0 4px 12px rgba(79, 70, 229, 0.4)',
              }}
            >
              {loading ? (
                <>
                  <RefreshCw size={15} className="animate-spin" />
                  Thinking...
                </>
              ) : (
                <>
                  <Send size={15} />
                  Ask Assistant
                </>
              )}
            </button>
          </div>

          {/* Chat Result Box */}
          {chatResult && (
            <div
              style={{
                backgroundColor: '#18181b',
                border: '1px solid #27272a',
                borderRadius: '10px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem',
                marginTop: '0.5rem',
              }}
            >
              {/* Question & Source Banner */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '12px',
                  paddingBottom: '10px',
                  borderBottom: '1px solid #27272a',
                  flexWrap: 'wrap',
                  gap: '8px',
                }}
              >
                <span style={{ fontWeight: 600, color: '#a1a1aa' }}>
                  Question:{' '}
                  <span style={{ color: '#ffffff', fontStyle: 'italic', fontWeight: 500 }}>
                    "{chatResult.question}"
                  </span>
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontFamily: 'monospace',
                      fontWeight: 600,
                      backgroundColor: chatResult.source === 'groq_llm' ? '#1e1b4b' : '#14532d',
                      color: chatResult.source === 'groq_llm' ? '#a5b4fc' : '#86efac',
                      border:
                        chatResult.source === 'groq_llm'
                          ? '1px solid #4338ca'
                          : '1px solid #166534',
                    }}
                  >
                    Source: {chatResult.source === 'groq_llm' ? 'Groq LLM' : 'Grounded Rule Engine'}
                  </span>
                  <span style={{ color: '#71717a', fontSize: '11px' }}>{chatResult.timeframe}</span>
                </div>
              </div>

              {/* Formatted Answer */}
              <div
                style={{
                  fontSize: '14px',
                  lineHeight: '1.65',
                  color: '#f1f5f9',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {chatResult.answer}
              </div>

              {/* Verified Facts Pills Container */}
              {Object.keys(chatResult.verified_facts || {}).length > 0 && (
                <div
                  style={{
                    backgroundColor: '#09090b',
                    border: '1px solid #27272a',
                    borderRadius: '8px',
                    padding: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                  }}
                >
                  <div
                    style={{
                      fontSize: '12px',
                      fontWeight: 700,
                      color: '#10b981',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <ShieldCheck size={15} />
                    Verified Database Facts Grounding:
                  </div>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {Object.entries(chatResult.verified_facts).map(([key, val]) => (
                      <div
                        key={key}
                        style={{
                          backgroundColor: '#18181b',
                          border: '1px solid #3f3f46',
                          borderRadius: '6px',
                          padding: '4px 10px',
                          fontSize: '12px',
                        }}
                      >
                        <span style={{ color: '#a1a1aa' }}>{key.replace(/_/g, ' ')}:</span>{' '}
                        <span style={{ fontWeight: 600, color: '#ffffff', fontFamily: 'monospace' }}>
                          {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Interpretations & Missing Telemetry */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  gap: '12px',
                }}
              >
                {chatResult.ai_interpretations && chatResult.ai_interpretations.length > 0 && (
                  <div
                    style={{
                      backgroundColor: 'rgba(79, 70, 229, 0.08)',
                      border: '1px solid rgba(99, 102, 241, 0.3)',
                      borderRadius: '8px',
                      padding: '12px',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: 700,
                        color: '#a5b4fc',
                        display: 'block',
                        marginBottom: '6px',
                      }}
                    >
                      AI Interpretations:
                    </span>
                    <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#cbd5e1' }}>
                      {chatResult.ai_interpretations.map((item, idx) => (
                        <li key={idx} style={{ marginBottom: '4px' }}>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {chatResult.missing_or_unavailable && chatResult.missing_or_unavailable.length > 0 && (
                  <div
                    style={{
                      backgroundColor: 'rgba(217, 119, 6, 0.08)',
                      border: '1px solid rgba(217, 119, 6, 0.3)',
                      borderRadius: '8px',
                      padding: '12px',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: 700,
                        color: '#fcd34d',
                        display: 'block',
                        marginBottom: '6px',
                      }}
                    >
                      Missing or Unavailable Telemetry:
                    </span>
                    <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#cbd5e1' }}>
                      {chatResult.missing_or_unavailable.map((item, idx) => (
                        <li key={idx} style={{ marginBottom: '4px' }}>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Repository Health Intelligence */}
      {activeTab === 'repo_health' && (
        <div style={{ marginTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '10px',
            }}
          >
            <span style={{ fontSize: '13px', color: '#e2e8f0', fontWeight: 500 }}>
              Telemetry Health Assessment for{' '}
              <span style={{ color: '#818cf8', fontFamily: 'monospace', fontWeight: 700 }}>
                {targetRepo || 'all'}
              </span>{' '}
              (Rolling 30-Day Window)
            </span>
            <button
              onClick={() => handleFetchRepoHealth(true)}
              disabled={loading}
              style={{
                fontSize: '12px',
                fontWeight: 600,
                backgroundColor: '#18181b',
                border: '1px solid #3f3f46',
                color: '#ffffff',
                padding: '6px 14px',
                borderRadius: '6px',
                cursor: loading ? 'wait' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              Force Regenerate
            </button>
          </div>

          {repoResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Summary Card */}
              <div
                style={{
                  backgroundColor: '#18181b',
                  border: '1px solid #27272a',
                  borderRadius: '10px',
                  padding: '1.25rem',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '8px',
                  }}
                >
                  <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: '#ffffff' }}>
                    Health Assessment
                  </h3>
                  <span
                    style={{
                      fontSize: '11px',
                      fontFamily: 'monospace',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      backgroundColor: '#27272a',
                      color: '#a5b4fc',
                    }}
                  >
                    Source: {repoResult.source}
                  </span>
                </div>
                <p style={{ fontSize: '14px', color: '#e2e8f0', lineHeight: 1.6, margin: '0 0 8px 0' }}>
                  {repoResult.health_summary}
                </p>
                <p style={{ fontSize: '12px', color: '#94a3b8', margin: 0 }}>
                  {repoResult.activity_analysis}
                </p>
              </div>

              {/* Facts Grid */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '12px',
                }}
              >
                <div
                  style={{
                    backgroundColor: '#18181b',
                    border: '1px solid #27272a',
                    borderRadius: '8px',
                    padding: '14px',
                  }}
                >
                  <span style={{ fontSize: '12px', color: '#a1a1aa', display: 'block', marginBottom: '4px' }}>
                    Total Commits (30d)
                  </span>
                  <span style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ffffff', fontFamily: 'monospace' }}>
                    {repoResult.verified_facts.total_commits}
                  </span>
                </div>

                <div
                  style={{
                    backgroundColor: '#18181b',
                    border: '1px solid #27272a',
                    borderRadius: '8px',
                    padding: '14px',
                  }}
                >
                  <span style={{ fontSize: '12px', color: '#a1a1aa', display: 'block', marginBottom: '4px' }}>
                    Open Pull Requests
                  </span>
                  <span style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ffffff', fontFamily: 'monospace' }}>
                    {repoResult.verified_facts.open_prs_count}
                  </span>
                </div>

                <div
                  style={{
                    backgroundColor: '#18181b',
                    border: '1px solid #27272a',
                    borderRadius: '8px',
                    padding: '14px',
                  }}
                >
                  <span style={{ fontSize: '12px', color: '#a1a1aa', display: 'block', marginBottom: '4px' }}>
                    Avg PR Cycle Time
                  </span>
                  <span style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ffffff', fontFamily: 'monospace' }}>
                    {repoResult.verified_facts.avg_pr_cycle_time_hours} hrs
                  </span>
                </div>

                <div
                  style={{
                    backgroundColor: '#18181b',
                    border: '1px solid #27272a',
                    borderRadius: '8px',
                    padding: '14px',
                  }}
                >
                  <span style={{ fontSize: '12px', color: '#a1a1aa', display: 'block', marginBottom: '4px' }}>
                    Code Churn Rate
                  </span>
                  <span style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ffffff', fontFamily: 'monospace' }}>
                    {(repoResult.verified_facts.code_churn_rate * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Recommendations and Patterns */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                  gap: '14px',
                }}
              >
                <div
                  style={{
                    backgroundColor: '#18181b',
                    border: '1px solid #27272a',
                    borderRadius: '10px',
                    padding: '1rem',
                  }}
                >
                  <h4
                    style={{
                      fontSize: '13px',
                      fontWeight: 700,
                      color: '#10b981',
                      margin: '0 0 10px 0',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <CheckCircle2 size={15} />
                    Strategic Recommendations
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#e2e8f0' }}>
                    {repoResult.strategic_recommendations.map((rec, i) => (
                      <li key={i} style={{ marginBottom: '6px' }}>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>

                <div
                  style={{
                    backgroundColor: '#18181b',
                    border: '1px solid #27272a',
                    borderRadius: '10px',
                    padding: '1rem',
                  }}
                >
                  <h4
                    style={{
                      fontSize: '13px',
                      fontWeight: 700,
                      color: '#f59e0b',
                      margin: '0 0 10px 0',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <Flame size={15} />
                    Activity Patterns & Observations
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#e2e8f0' }}>
                    {repoResult.unusual_patterns.map((pat, i) => (
                      <li key={i} style={{ marginBottom: '6px' }}>
                        {pat}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Weekly Team Engineering Report */}
      {activeTab === 'team_report' && (
        <div style={{ marginTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '10px',
            }}
          >
            <span style={{ fontSize: '13px', color: '#e2e8f0', fontWeight: 500 }}>
              Weekly Team Engineering Report for{' '}
              <span style={{ color: '#818cf8', fontFamily: 'monospace', fontWeight: 700 }}>
                {targetRepo || 'all'}
              </span>{' '}
              (Last 7 Days)
            </span>
            <button
              onClick={() => handleFetchTeamReport(true)}
              disabled={loading}
              style={{
                fontSize: '12px',
                fontWeight: 600,
                backgroundColor: '#18181b',
                border: '1px solid #3f3f46',
                color: '#ffffff',
                padding: '6px 14px',
                borderRadius: '6px',
                cursor: loading ? 'wait' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              Regenerate Report
            </button>
          </div>

          {teamResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div
                style={{
                  backgroundColor: '#18181b',
                  border: '1px solid #27272a',
                  borderRadius: '10px',
                  padding: '1.25rem',
                }}
              >
                <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: '0 0 8px 0', color: '#ffffff' }}>
                  Weekly Executive Engineering Summary
                </h3>
                <p style={{ fontSize: '14px', color: '#e2e8f0', lineHeight: 1.65, margin: '0 0 8px 0' }}>
                  {teamResult.weekly_report}
                </p>
                <p style={{ fontSize: '12px', color: '#94a3b8', margin: 0 }}>
                  {teamResult.contribution_distribution_analysis}
                </p>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                  gap: '14px',
                }}
              >
                <div
                  style={{
                    backgroundColor: '#18181b',
                    border: '1px solid #27272a',
                    borderRadius: '10px',
                    padding: '1rem',
                  }}
                >
                  <h4
                    style={{
                      fontSize: '13px',
                      fontWeight: 700,
                      color: '#f87171',
                      margin: '0 0 10px 0',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <AlertCircle size={15} />
                    Review Bottlenecks
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#e2e8f0' }}>
                    {teamResult.review_bottlenecks.map((b, i) => (
                      <li key={i} style={{ marginBottom: '6px' }}>
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>

                <div
                  style={{
                    backgroundColor: '#18181b',
                    border: '1px solid #27272a',
                    borderRadius: '10px',
                    padding: '1rem',
                  }}
                >
                  <h4
                    style={{
                      fontSize: '13px',
                      fontWeight: 700,
                      color: '#818cf8',
                      margin: '0 0 10px 0',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <ShieldCheck size={15} />
                    Actionable Team Directives
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#e2e8f0' }}>
                    {teamResult.team_recommendations.map((rec, i) => (
                      <li key={i} style={{ marginBottom: '6px' }}>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
