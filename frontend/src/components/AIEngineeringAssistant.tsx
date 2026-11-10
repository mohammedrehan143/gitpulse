import React, { useState } from 'react';
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
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl text-slate-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
              AI
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                Engineering Intelligence Assistant
                <span className="text-xs font-mono font-medium bg-indigo-950 text-indigo-300 border border-indigo-700/50 px-2 py-0.5 rounded-full">
                  Groq LLM + Strict Grounding
                </span>
              </h2>
              <p className="text-sm text-slate-400">
                Natural-language Q&A and analytics grounded strictly in database facts (no hallucination).
              </p>
            </div>
          </div>
        </div>

        {/* Target Repository Selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Context Repo:</label>
          <select
            value={targetRepo}
            onChange={(e) => setTargetRepo(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
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

      {/* Tabs */}
      <div className="flex border-b border-slate-800 mt-4 gap-6">
        <button
          onClick={() => setActiveTab('assistant')}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'assistant'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Engineering Assistant Q&A
        </button>
        <button
          onClick={() => {
            setActiveTab('repo_health');
            if (!repoResult && targetRepo) handleFetchRepoHealth();
          }}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'repo_health'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Repository Health Intelligence
        </button>
        <button
          onClick={() => {
            setActiveTab('team_report');
            if (!teamResult && targetRepo) handleFetchTeamReport();
          }}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'team_report'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Weekly Team Engineering Report
        </button>
      </div>

      {/* Error alert */}
      {error && (
        <div className="mt-4 p-3 bg-rose-950/60 border border-rose-800/80 rounded-lg text-rose-300 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs text-rose-400 hover:text-rose-200">
            Dismiss
          </button>
        </div>
      )}

      {/* TAB 1: Natural Language Assistant */}
      {activeTab === 'assistant' && (
        <div className="mt-6 space-y-6">
          {/* Quick preset chips */}
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
              Suggested Questions:
            </span>
            <div className="flex flex-wrap gap-2">
              {presetQuestions.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSendQuestion(q)}
                  disabled={loading}
                  className="text-xs bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700 px-3 py-1.5 rounded-full transition-all disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Input Box */}
          <div className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendQuestion()}
              placeholder="Ask anything about commit velocity, pull requests, inactive repos, or contributors..."
              disabled={loading}
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            <button
              onClick={() => handleSendQuestion()}
              disabled={loading || !question.trim()}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium px-5 py-2.5 rounded-lg text-sm transition-all shadow-md flex items-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Thinking...
                </>
              ) : (
                'Ask Assistant'
              )}
            </button>
          </div>

          {/* Chat Result Display */}
          {chatResult && (
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-4 mt-6">
              <div className="flex items-center justify-between text-xs pb-3 border-b border-slate-800/80">
                <span className="font-semibold text-slate-300">
                  Q: <span className="text-slate-100 font-normal">"{chatResult.question}"</span>
                </span>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-indigo-950 text-indigo-300 border border-indigo-800">
                    Source: {chatResult.source === 'groq_llm' ? 'Groq LLM' : 'Grounded Rule Engine'}
                  </span>
                  <span className="text-slate-500 text-[11px]">{chatResult.timeframe}</span>
                </div>
              </div>

              {/* Main Answer */}
              <div className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap">
                {chatResult.answer}
              </div>

              {/* Verified Database Facts */}
              {Object.keys(chatResult.verified_facts || {}).length > 0 && (
                <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3 text-xs space-y-2">
                  <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                    Verified Database Facts Grounding:
                  </div>
                  <div className="flex flex-wrap gap-2 text-slate-300">
                    {Object.entries(chatResult.verified_facts).map(([key, val]) => (
                      <div key={key} className="bg-slate-800 border border-slate-700/60 px-2.5 py-1 rounded">
                        <span className="text-slate-400">{key.replace(/_/g, ' ')}:</span>{' '}
                        <span className="font-mono font-medium text-slate-200">
                          {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* AI Interpretations vs Missing Info */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-2">
                {chatResult.ai_interpretations?.length > 0 && (
                  <div className="bg-indigo-950/30 border border-indigo-900/40 rounded-lg p-3">
                    <span className="font-semibold text-indigo-300 block mb-1">AI Interpretations:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-slate-400">
                      {chatResult.ai_interpretations.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {chatResult.missing_or_unavailable?.length > 0 && (
                  <div className="bg-amber-950/20 border border-amber-900/30 rounded-lg p-3">
                    <span className="font-semibold text-amber-300 block mb-1">Unavailable / Missing Telemetry:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-slate-400">
                      {chatResult.missing_or_unavailable.map((item, idx) => (
                        <li key={idx}>{item}</li>
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
        <div className="mt-6 space-y-6">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-300 font-medium">
              Intelligence Assessment for <span className="text-indigo-400 font-mono">{targetRepo || 'all'}</span> (Last 30 Days)
            </span>
            <button
              onClick={() => handleFetchRepoHealth(true)}
              disabled={loading}
              className="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 px-3 py-1.5 rounded transition-all"
            >
              Force Refresh Analysis
            </button>
          </div>

          {repoResult && (
            <div className="space-y-4">
              {/* Summary Card */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-slate-100">Health Summary</h3>
                  <span className="text-xs font-mono bg-slate-800 border border-slate-700 px-2.5 py-0.5 rounded text-indigo-300">
                    Source: {repoResult.source}
                  </span>
                </div>
                <p className="text-sm text-slate-300">{repoResult.health_summary}</p>
                <p className="text-xs text-slate-400">{repoResult.activity_analysis}</p>
              </div>

              {/* Verified Facts Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-slate-950/60 border border-slate-800/80 p-3 rounded-lg">
                  <span className="text-xs text-slate-400 block">Total Commits (30d)</span>
                  <span className="text-lg font-bold font-mono text-slate-100">{repoResult.verified_facts.total_commits}</span>
                </div>
                <div className="bg-slate-950/60 border border-slate-800/80 p-3 rounded-lg">
                  <span className="text-xs text-slate-400 block">Open Pull Requests</span>
                  <span className="text-lg font-bold font-mono text-slate-100">{repoResult.verified_facts.open_prs_count}</span>
                </div>
                <div className="bg-slate-950/60 border border-slate-800/80 p-3 rounded-lg">
                  <span className="text-xs text-slate-400 block">Avg PR Cycle Time</span>
                  <span className="text-lg font-bold font-mono text-slate-100">{repoResult.verified_facts.avg_pr_cycle_time_hours} hrs</span>
                </div>
                <div className="bg-slate-950/60 border border-slate-800/80 p-3 rounded-lg">
                  <span className="text-xs text-slate-400 block">Code Churn Rate</span>
                  <span className="text-lg font-bold font-mono text-slate-100">{(repoResult.verified_facts.code_churn_rate * 100).toFixed(1)}%</span>
                </div>
              </div>

              {/* Recommendations & Patterns */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-950/70 border border-slate-800 p-4 rounded-xl space-y-2">
                  <h4 className="text-sm font-semibold text-emerald-400">Strategic Recommendations</h4>
                  <ul className="list-disc list-inside text-xs text-slate-300 space-y-1">
                    {repoResult.strategic_recommendations.map((rec, i) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
                </div>
                <div className="bg-slate-950/70 border border-slate-800 p-4 rounded-xl space-y-2">
                  <h4 className="text-sm font-semibold text-amber-400">Activity Patterns & Observations</h4>
                  <ul className="list-disc list-inside text-xs text-slate-300 space-y-1">
                    {repoResult.unusual_patterns.map((pat, i) => (
                      <li key={i}>{pat}</li>
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
        <div className="mt-6 space-y-6">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-300 font-medium">
              Weekly Report for <span className="text-indigo-400 font-mono">{targetRepo || 'all'}</span> (Last 7 Days)
            </span>
            <button
              onClick={() => handleFetchTeamReport(true)}
              disabled={loading}
              className="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 px-3 py-1.5 rounded transition-all"
            >
              Regenerate Report
            </button>
          </div>

          {teamResult && (
            <div className="space-y-4">
              <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-3">
                <h3 className="text-base font-bold text-slate-100">Weekly Executive Engineering Summary</h3>
                <p className="text-sm text-slate-200 leading-relaxed">{teamResult.weekly_report}</p>
                <p className="text-xs text-slate-400">{teamResult.contribution_distribution_analysis}</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-950/70 border border-slate-800 p-4 rounded-xl space-y-2">
                  <h4 className="text-sm font-semibold text-rose-400">Review Bottlenecks</h4>
                  <ul className="list-disc list-inside text-xs text-slate-300 space-y-1">
                    {teamResult.review_bottlenecks.map((b, i) => (
                      <li key={i}>{b}</li>
                    ))}
                  </ul>
                </div>
                <div className="bg-slate-950/70 border border-slate-800 p-4 rounded-xl space-y-2">
                  <h4 className="text-sm font-semibold text-indigo-400">Actionable Team Directives</h4>
                  <ul className="list-disc list-inside text-xs text-slate-300 space-y-1">
                    {teamResult.team_recommendations.map((rec, i) => (
                      <li key={i}>{rec}</li>
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
