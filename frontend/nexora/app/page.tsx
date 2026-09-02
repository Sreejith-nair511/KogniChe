'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity, ArrowUpRight, BarChart3, Bookmark, Check, ChevronDown, ChevronRight,
  CircleHelp, Compass, Database, ExternalLink, Filter, Heart, Home,
  Info, Layers3, Menu, MoreHorizontal, PanelRight, Play, Plus, Search, Settings2,
  SlidersHorizontal, Sparkles, Target, ThumbsDown, ThumbsUp, UserRound, X, Zap,
  TrendingUp, TrendingDown, Minus,
} from 'lucide-react'
import {
  search, recordInteraction, getProfile, getHealth, getEvaluationSummary,
  getEvaluationComparison, listUsers,
  type RecommendationItem, type SearchResponse, type ProfileSummary,
  type HealthResponse, type EvaluationSummary, type EvaluationComparison,
  type DNADimension,
} from '@/lib/api'

// ── Types ──────────────────────────────────────────────────────────────────────
type View = 'Discover' | 'For You' | 'Saved' | 'Profile' | 'Evaluation' | 'System'

// ── Stable session / user IDs ──────────────────────────────────────────────────
function getOrCreate(key: string, factory: () => string): string {
  if (typeof window === 'undefined') return factory()
  const v = localStorage.getItem(key)
  if (v) return v
  const n = factory()
  localStorage.setItem(key, n)
  return n
}
const genId = (prefix: string) => `${prefix}_${Math.random().toString(36).slice(2, 14)}`

// ── Navigation ─────────────────────────────────────────────────────────────────
const nav: { label: View; icon: typeof Compass }[] = [
  { label: 'Discover', icon: Compass },
  { label: 'For You', icon: Sparkles },
  { label: 'Saved', icon: Bookmark },
  { label: 'Profile', icon: UserRound },
  { label: 'Evaluation', icon: BarChart3 },
  { label: 'System', icon: Settings2 },
]

// ── Logo ───────────────────────────────────────────────────────────────────────
function Logo() {
  return (
    <div className="flex items-center gap-3">
      <div className="logo-mark"><span /></div>
      <span className="text-sm font-semibold tracking-[0.28em]">NEXORA</span>
    </div>
  )
}

// ── Sidebar ────────────────────────────────────────────────────────────────────
function Sidebar({
  view, setView, mobileOpen, setMobileOpen, savedCount, profile,
}: {
  view: View; setView: (v: View) => void
  mobileOpen: boolean; setMobileOpen: (v: boolean) => void
  savedCount: number; profile: ProfileSummary | null
}) {
  const confidence = profile?.dna?.confidence ?? 0
  const maturityLabel = profile?.profile_maturity ?? 'cold_start'
  const pct = Math.round(confidence * 100)

  return (
    <aside className={`sidebar ${mobileOpen ? 'is-open' : ''}`}>
      <div className="flex items-center justify-between px-5 py-5">
        <Logo />
        <button className="mobile-close" aria-label="Close menu" onClick={() => setMobileOpen(false)}><X size={18} /></button>
      </div>
      <div className="px-3 pt-8">
        <p className="eyebrow px-3 pb-3">Workspace</p>
        <nav className="flex flex-col gap-1">
          {nav.map(({ label, icon: Icon }) => (
            <button
              key={label}
              onClick={() => { setView(label); setMobileOpen(false) }}
              className={`nav-item ${view === label ? 'active' : ''}`}
            >
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
              {label === 'Saved' && savedCount > 0 && (
                <span className="ml-auto text-[11px] text-muted-foreground">{savedCount}</span>
              )}
            </button>
          ))}
        </nav>
      </div>
      <div className="mt-auto px-5 pb-6">
        <div className="signal-card">
          <div className="flex items-center gap-2 text-xs font-medium">
            <span className="live-dot" />
            {maturityLabel === 'cold_start' ? 'Building your model' : 'System healthy'}
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
            {profile
              ? `${profile.interaction_count} signals learned · ${maturityLabel} profile`
              : 'Your personal model is learning from every signal.'}
          </p>
          <div className="mt-4 h-1 overflow-hidden rounded-full bg-border">
            <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
          </div>
          <div className="mt-2 flex justify-between text-[10px] text-muted-foreground">
            <span>DNA confidence</span>
            <span>{pct}%</span>
          </div>
        </div>
        <button className="mt-5 flex items-center gap-2 px-1 text-xs text-muted-foreground hover:text-foreground">
          <CircleHelp size={14} /> Help & documentation
        </button>
      </div>
    </aside>
  )
}

// ── Topbar ─────────────────────────────────────────────────────────────────────
function Topbar({
  setMobileOpen, prompt, setPrompt, onSubmit, profile,
}: {
  setMobileOpen: (v: boolean) => void
  prompt: string; setPrompt: (v: string) => void
  onSubmit: () => void
  profile: ProfileSummary | null
}) {
  const initials = profile?.display_name
    ? profile.display_name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'JD'

  return (
    <header className="topbar">
      <button className="mobile-menu" aria-label="Open menu" onClick={() => setMobileOpen(true)}><Menu size={20} /></button>
      <div className="command-wrap">
        <Search size={16} className="text-muted-foreground" />
        <input
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.nativeEvent.isComposing && e.keyCode !== 229) onSubmit()
          }}
          placeholder="Ask NEXORA anything..."
          aria-label="Ask NEXORA anything"
        />
        <kbd>⌘ K</kbd>
      </div>
      <div className="top-actions">
        <button aria-label="Activity"><Activity size={17} /></button>
        <button aria-label="Notifications"><span className="notification" /></button>
        <div className="avatar" title={profile?.display_name ?? 'Guest'}>{initials}</div>
      </div>
    </header>
  )
}

// ── Match Ring ─────────────────────────────────────────────────────────────────
function MatchRing({ score }: { score: number }) {
  return (
    <div className="match-ring">
      <svg viewBox="0 0 36 36">
        <circle cx="18" cy="18" r="15" />
        <circle className="ring-progress" cx="18" cy="18" r="15" pathLength="100" style={{ strokeDasharray: `${score} 100` }} />
      </svg>
      <span>{score}</span>
    </div>
  )
}

// ── Rank Change Badge ──────────────────────────────────────────────────────────
function RankBadge({ change }: { change: RecommendationItem['rank_change'] }) {
  if (!change || change.direction === 'unchanged' || change.direction === 'new') return null
  const isUp = change.direction === 'up'
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded"
      style={{
        background: isUp ? 'oklch(.76 .16 174 / .15)' : 'oklch(.66 .18 25 / .15)',
        color: isUp ? 'var(--primary)' : 'var(--destructive)',
      }}
      title={`Moved ${isUp ? 'up' : 'down'} ${Math.abs(change.rank_delta)} ${Math.abs(change.rank_delta) === 1 ? 'place' : 'places'}`}
    >
      {isUp ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
      {Math.abs(change.rank_delta)}
    </span>
  )
}

// ── Recommendation Card ────────────────────────────────────────────────────────
function RecommendationCard({
  item, liked, saved, onLike, onSave, onDislike, onWhy,
}: {
  item: RecommendationItem
  liked: boolean; saved: boolean
  onLike: () => void; onSave: () => void; onDislike: () => void; onWhy: () => void
}) {
  const eyebrow = [item.entity_type.toUpperCase(), item.category?.toUpperCase()].filter(Boolean).join(' / ')
  const imgSrc = item.image ?? 'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=800&q=80'

  return (
    <article className="recommendation-card">
      <div className="card-image">
        <img src={imgSrc} alt="" loading="lazy" />
        <div className="image-overlay" />
        <div className="card-top">
          <div className="flex items-center gap-2">
            <span className="match-pill"><Sparkles size={12} /> {item.match_percentage}% match</span>
            <RankBadge change={item.rank_change} />
          </div>
          <button className="icon-button dark" aria-label="More options"><MoreHorizontal size={17} /></button>
        </div>
        <div className="card-copy">
          <p className="eyebrow text-white/70">{eyebrow}</p>
          <h3>{item.title}</h3>
          {item.city && <p className="text-white/60 text-xs mt-1">{item.city}, {item.country}</p>}
        </div>
      </div>
      <div className="card-body">
        <p className="text-sm leading-relaxed text-muted-foreground line-clamp-2">{item.description}</p>
        <div className="mt-3 flex items-center gap-3 text-[11px] text-muted-foreground">
          {item.price?.display && (
            <span className="text-foreground/80">{item.price.display}</span>
          )}
          {item.rating && (
            <span>★ {item.rating.toFixed(1)}</span>
          )}
          {item.duration && <span>{item.duration}</span>}
          <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded ${
            item.confidence === 'HIGH' ? 'bg-primary/10 text-primary' :
            item.confidence === 'LOW' ? 'bg-destructive/10 text-destructive' :
            'bg-secondary text-muted-foreground'
          }`}>
            {item.confidence}
          </span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {item.tags.slice(0, 4).map(tag => <span className="tag" key={tag}>{tag}</span>)}
        </div>
        <div className="mt-5 flex items-center justify-between border-t border-border pt-4">
          <button onClick={onWhy} className="why-link"><Info size={14} /> Why this?</button>
          <div className="flex items-center gap-1">
            <button onClick={onLike} className={`action-button ${liked ? 'selected' : ''}`} aria-label="Like">
              <Heart size={15} fill={liked ? 'currentColor' : 'none'} />
            </button>
            <button onClick={onSave} className={`action-button ${saved ? 'selected' : ''}`} aria-label="Save">
              <Bookmark size={15} fill={saved ? 'currentColor' : 'none'} />
            </button>
            <button onClick={onDislike} className="action-button" aria-label="Not interested">
              <ThumbsDown size={15} />
            </button>
          </div>
        </div>
      </div>
    </article>
  )
}

// ── Discover View ──────────────────────────────────────────────────────────────
function Discover({
  prompt, setPrompt, processing, onWhy, recommendations, retrieval, onSearch,
  onLike, onSave, onDislike, likedIds, savedIds,
}: {
  prompt: string; setPrompt: (v: string) => void
  processing: boolean
  onWhy: (item: RecommendationItem) => void
  recommendations: RecommendationItem[]
  retrieval: SearchResponse['retrieval'] | null
  onSearch: () => void
  onLike: (item: RecommendationItem) => void
  onSave: (item: RecommendationItem) => void
  onDislike: (item: RecommendationItem) => void
  likedIds: Set<string>; savedIds: Set<string>
}) {
  const suggestions = ['Beach adventure activities', 'Budget heritage stays in Jaipur', 'Family wellness packages']

  return (
    <div className="page-content">
      <section className="hero-section">
        <div>
          <p className="eyebrow accent-label"><span className="sparkle-dot" />Personal intelligence layer</p>
          <h1>Discover what<br /><em>moves</em> you.</h1>
          <p className="hero-sub">NEXORA connects the dots between your curiosity, your context, and real travel data.</p>
        </div>
        <div className="hero-orbit">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="orbit-core"><Sparkles size={18} /></div>
          <span className="orbit-label label-a">context</span>
          <span className="orbit-label label-b">curiosity</span>
          <span className="orbit-label label-c">signal</span>
        </div>
      </section>

      <section className="prompt-panel">
        <div className="prompt-header">
          <div className="flex items-center gap-2">
            <div className="pulse-icon"><Zap size={14} /></div>
            <span>Guide the signal</span>
          </div>
          <span className="text-[11px] text-muted-foreground">Natural language · multilingual</span>
        </div>
        <div className="prompt-input">
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing && e.keyCode !== 229) {
                e.preventDefault(); onSearch()
              }
            }}
            placeholder="What are you looking for? (English, हिन्दी, தமிழ், ...)"
            rows={2}
          />
          <button onClick={onSearch} className="send-button" aria-label="Run query" disabled={processing}>
            <ArrowUpRight size={19} />
          </button>
        </div>
        <div className="prompt-suggestions">
          <span>Try</span>
          {suggestions.map(s => (
            <button key={s} onClick={() => { setPrompt(s); }}>{s}<ChevronRight size={12} /></button>
          ))}
        </div>
      </section>

      {processing && (
        <div className="processing-bar">
          <span className="live-dot" />
          <span>Reading your signal...</span>
          <div className="processing-line"><div /></div>
          <span className="text-muted-foreground">Retrieving · Reranking · Explaining</span>
        </div>
      )}

      <div className="section-heading">
        <div>
          <p className="eyebrow">Curated for this moment</p>
          <h2>Signals worth following</h2>
        </div>
        <div className="flex items-center gap-2">
          <button className="filter-button"><Filter size={14} /> All types<ChevronDown size={13} /></button>
          <button className="icon-button" aria-label="More filters"><SlidersHorizontal size={16} /></button>
        </div>
      </div>

      {recommendations.length === 0 && !processing && (
        <div className="empty-note" style={{ marginBottom: '24px' }}>
          <Layers3 size={18} />
          <div>
            <p className="text-sm font-medium">Search to discover recommendations</p>
            <p className="text-xs text-muted-foreground">Try "beach adventure in Goa" or "budget heritage hotel Jaipur"</p>
          </div>
        </div>
      )}

      <div className="recommendations-grid">
        {recommendations.map(item => (
          <RecommendationCard
            key={item.entity_id}
            item={item}
            liked={likedIds.has(item.entity_id)}
            saved={savedIds.has(item.entity_id)}
            onLike={() => onLike(item)}
            onSave={() => onSave(item)}
            onDislike={() => onDislike(item)}
            onWhy={() => onWhy(item)}
          />
        ))}
      </div>

      {retrieval && (
        <div className="retrieval-row">
          <div className="flex items-center gap-3">
            <div className="retrieval-icon"><Database size={16} /></div>
            <div>
              <p className="text-xs font-medium">Retrieval context</p>
              <p className="text-[11px] text-muted-foreground">
                {retrieval.eligible_count} eligible · {retrieval.semantic_candidate_count} semantic · {retrieval.final_count} results · {Math.round(retrieval.total_ms)}ms
              </p>
            </div>
          </div>
          <span className="text-xs text-muted-foreground">
            {retrieval.catalogue_count} in catalogue
          </span>
        </div>
      )}
    </div>
  )
}

// ── Intelligence Rail ──────────────────────────────────────────────────────────
function Rail({
  setView, profile, sessionSignalCount,
}: {
  setView: (v: View) => void
  profile: ProfileSummary | null
  sessionSignalCount: number
}) {
  const dna = profile?.dna
  const topDims: DNADimension[] = dna
    ? [...dna.dimensions].sort((a, b) => b.score - a.score).slice(0, 4)
    : [
        { dimension: 'Adventure', score: 0, previous_score: null, change: 0 },
        { dimension: 'Culture', score: 0, previous_score: null, change: 0 },
        { dimension: 'Nature', score: 0, previous_score: null, change: 0 },
        { dimension: 'Relaxation', score: 0, previous_score: null, change: 0 },
      ]

  const confidencePct = dna ? Math.round(dna.confidence * 100) : 0
  const signalStrength = profile
    ? Math.min(0.4 + profile.maturity_score * 0.6, 0.99).toFixed(2)
    : '0.00'

  return (
    <aside className="intelligence-rail">
      <div className="rail-heading">
        <div>
          <p className="eyebrow">Your intelligence</p>
          <h3>Profile DNA</h3>
        </div>
        <button className="icon-button"><PanelRight size={15} /></button>
      </div>

      <div className="dna-visual">
        <div className="dna-ring ring-a" />
        <div className="dna-ring ring-b" />
        <div className="dna-ring ring-c" />
        <div className="dna-center">
          <span>{confidencePct}</span>
          <small>confidence</small>
        </div>
      </div>

      <div className="dna-bars">
        {topDims.map(d => (
          <div key={d.dimension} className="dna-bar">
            <div className="flex justify-between text-[11px]">
              <span>{d.dimension}</span>
              <span className="text-muted-foreground">{Math.round(d.score * 100)}%</span>
            </div>
            <div className="mt-2 h-1 rounded-full bg-border">
              <div className="h-full rounded-full bg-primary" style={{ width: `${Math.round(d.score * 100)}%` }} />
            </div>
          </div>
        ))}
      </div>

      <button onClick={() => setView('Profile')} className="rail-link">
        Explore your profile <ArrowUpRight size={14} />
      </button>

      <div className="rail-divider" />

      <div className="rail-heading">
        <div>
          <p className="eyebrow">Live session</p>
          <h3>Signal strength</h3>
        </div>
        <span className="live-dot" />
      </div>

      <div className="signal-score">
        <span>{signalStrength}</span>
        <div>
          <p>{profile?.profile_maturity === 'mature' ? 'High relevance' : profile?.profile_maturity === 'learning' ? 'Learning' : 'Building'}</p>
          <p className="text-[11px] text-muted-foreground">
            {sessionSignalCount > 0 ? `Based on ${sessionSignalCount} session signals` : `${profile?.interaction_count ?? 0} lifetime signals`}
          </p>
        </div>
      </div>

      <div className="mini-wave">
        {Array.from({ length: 12 }).map((_, i) => <i key={i} />)}
      </div>
    </aside>
  )
}

// ── Profile View ───────────────────────────────────────────────────────────────
function ProfileView({ profile }: { profile: ProfileSummary | null }) {
  if (!profile) {
    return (
      <div className="page-content simple-view">
        <p className="eyebrow accent-label"><Sparkles size={13} /> NEXORA / Profile</p>
        <h1>The shape of your curiosity.</h1>
        <p className="hero-sub">Loading your profile...</p>
      </div>
    )
  }

  const dna = profile.dna
  const dims = dna ? [...dna.dimensions].sort((a, b) => b.score - a.score) : []

  return (
    <div className="page-content simple-view">
      <p className="eyebrow accent-label"><Sparkles size={13} /> NEXORA / Profile</p>
      <h1>{profile.display_name ?? 'Your profile'}</h1>
      <p className="hero-sub">
        {profile.segment} user · {profile.profile_maturity} · {profile.interaction_count} signals
      </p>

      <div className="simple-grid">
        <div className="metric-panel">
          <p className="eyebrow">Profile confidence</p>
          <div className="big-metric">{Math.round((dna?.confidence ?? 0) * 100)}<span>%</span></div>
          <p className="text-sm text-muted-foreground">{profile.profile_maturity} profile · {profile.interaction_count} lifetime interactions</p>
        </div>
        <div className="metric-panel">
          <p className="eyebrow">Travel style</p>
          <div className="big-metric" style={{ fontSize: '28px', marginTop: '18px', letterSpacing: '-.02em' }}>
            {profile.travel_style ?? '—'}
          </div>
          <p className="text-sm text-muted-foreground">
            {profile.traveller_type} · {profile.budget_band} budget · {profile.pace} pace
          </p>
        </div>
      </div>

      {dims.length > 0 && (
        <div className="metric-panel" style={{ marginTop: '16px' }}>
          <p className="eyebrow" style={{ marginBottom: '16px' }}>DNA dimensions</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {dims.map(d => (
              <div key={d.dimension}>
                <div className="flex justify-between text-[12px] mb-1">
                  <span>{d.dimension}</span>
                  <span className="text-muted-foreground">{Math.round(d.score * 100)}%</span>
                </div>
                <div className="h-1 rounded-full bg-border">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${Math.round(d.score * 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="metric-panel" style={{ marginTop: '16px' }}>
        <p className="eyebrow" style={{ marginBottom: '12px' }}>Preferences</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
          {profile.preferred_languages.length > 0 && (
            <div><span className="text-muted-foreground">Languages: </span>{profile.preferred_languages.join(', ')}</div>
          )}
          {profile.preferred_currency && (
            <div><span className="text-muted-foreground">Currency: </span>{profile.preferred_currency}</div>
          )}
          {profile.max_daily_budget && (
            <div><span className="text-muted-foreground">Daily budget: </span>{profile.max_daily_budget} {profile.max_daily_budget_currency}</div>
          )}
          {profile.locale && (
            <div><span className="text-muted-foreground">Locale: </span>{profile.locale}</div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Evaluation View ────────────────────────────────────────────────────────────
function EvaluationView() {
  const [summary, setSummary] = useState<EvaluationSummary | null>(null)
  const [comparison, setComparison] = useState<EvaluationComparison | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runEval = async () => {
    setLoading(true); setError(null)
    try {
      const [s, c] = await Promise.all([
        getEvaluationSummary(30),
        getEvaluationComparison(20),
      ])
      setSummary(s); setComparison(c)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Evaluation failed')
    } finally {
      setLoading(false)
    }
  }

  const models = comparison ? [
    { name: 'Popularity', m: comparison.popularity },
    { name: 'Semantic', m: comparison.semantic },
    { name: 'Hybrid', m: comparison.hybrid },
    { name: 'NEXORA', m: comparison.nexora },
  ] : []

  return (
    <div className="page-content simple-view">
      <p className="eyebrow accent-label"><Sparkles size={13} /> NEXORA / Evaluation</p>
      <h1>Measure the signal.</h1>
      <p className="hero-sub">Real metrics against APS-04 eval queries and relevance labels. No fabricated numbers.</p>

      <div className="flex gap-3 mt-8">
        <button className="filter-button" onClick={runEval} disabled={loading}>
          {loading ? 'Running...' : 'Run evaluation'} <Play size={13} />
        </button>
        {summary && (
          <span className="text-xs text-muted-foreground self-center">{summary.number_of_queries} queries evaluated</span>
        )}
      </div>

      {error && <p className="text-sm text-destructive mt-4">{error}</p>}

      {summary && (
        <div className="simple-grid" style={{ marginTop: '24px' }}>
          {[
            { label: 'NDCG@10', value: summary.ndcg_at_10 },
            { label: 'Precision@10', value: summary.precision_at_10 },
            { label: 'NDCG@5', value: summary.ndcg_at_5 },
            { label: 'MRR', value: summary.mrr },
          ].map(({ label, value }) => (
            <div key={label} className="metric-panel">
              <p className="eyebrow">{label}</p>
              <div className="big-metric">{value.toFixed(3)}</div>
            </div>
          ))}
        </div>
      )}

      {comparison && (
        <div className="metric-panel" style={{ marginTop: '16px' }}>
          <p className="eyebrow" style={{ marginBottom: '16px' }}>Model comparison</p>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Model', 'P@5', 'P@10', 'NDCG@5', 'NDCG@10', 'Recall@10', 'MRR'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--muted-foreground)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {models.map(({ name, m }) => (
                  <tr key={name} style={{ borderBottom: '1px solid var(--border)', background: name === 'NEXORA' ? 'oklch(.76 .16 174 / .05)' : undefined }}>
                    <td style={{ padding: '6px 10px', fontWeight: name === 'NEXORA' ? 600 : 400, color: name === 'NEXORA' ? 'var(--primary)' : undefined }}>{name}</td>
                    <td style={{ padding: '6px 10px' }}>{m.precision_at_5.toFixed(4)}</td>
                    <td style={{ padding: '6px 10px' }}>{m.precision_at_10.toFixed(4)}</td>
                    <td style={{ padding: '6px 10px' }}>{m.ndcg_at_5.toFixed(4)}</td>
                    <td style={{ padding: '6px 10px' }}>{m.ndcg_at_10.toFixed(4)}</td>
                    <td style={{ padding: '6px 10px' }}>{m.recall_at_10.toFixed(4)}</td>
                    <td style={{ padding: '6px 10px' }}>{m.mrr.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[10px] text-muted-foreground mt-3">Ground truth: APS-04 eval_relevance_labels (grades 0–3). Relevance threshold ≥2.</p>
        </div>
      )}
    </div>
  )
}

// ── System View ────────────────────────────────────────────────────────────────
function SystemView() {
  const [health, setHealth] = useState<HealthResponse | null>(null)

  useEffect(() => {
    getHealth().then(setHealth).catch(() => {})
  }, [])

  const statusColor = (s: string) =>
    s === 'ok' ? 'var(--primary)' : s === 'degraded' ? 'oklch(.8 .15 80)' : 'var(--destructive)'

  return (
    <div className="page-content simple-view">
      <p className="eyebrow accent-label"><Sparkles size={13} /> NEXORA / System</p>
      <h1>System status.</h1>
      <p className="hero-sub">Your intelligence layer is online and learning.</p>

      <div className="metric-panel" style={{ marginTop: '48px' }}>
        <p className="eyebrow" style={{ marginBottom: '16px' }}>Health check</p>
        {!health ? (
          <p className="text-sm text-muted-foreground">Checking backend...</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
            {[
              ['API', health.api],
              ['Database', health.database],
              ['Vector index', health.vector_index],
              ['Embedding model', health.embedding_model],
              ['Dataset', health.dataset],
            ].map(([label, status]) => (
              <div key={label} className="flex items-center justify-between">
                <span>{label}</span>
                <span style={{ color: statusColor(status), fontWeight: 500 }}>{status}</span>
              </div>
            ))}
          </div>
        )}
        {health?.details && (
          <div style={{ marginTop: '16px', fontSize: '11px', color: 'var(--muted-foreground)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {health.details.users !== undefined && <span>Users: {String(health.details.users)}</span>}
            {health.details.hotels !== undefined && <span>Hotels: {String(health.details.hotels)}</span>}
            {health.details.activities_poi !== undefined && <span>POIs: {String(health.details.activities_poi)}</span>}
            {health.details.vector_index_vectors !== undefined && <span>Vectors indexed: {String(health.details.vector_index_vectors)}</span>}
            {health.details.warning && <span style={{ color: 'oklch(.8 .15 80)' }}>⚠ {String(health.details.warning)}</span>}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Saved View ─────────────────────────────────────────────────────────────────
function SavedView({
  savedItems, onWhy, likedIds, savedIds, onLike, onSave, onDislike,
}: {
  savedItems: RecommendationItem[]
  onWhy: (item: RecommendationItem) => void
  likedIds: Set<string>; savedIds: Set<string>
  onLike: (item: RecommendationItem) => void
  onSave: (item: RecommendationItem) => void
  onDislike: (item: RecommendationItem) => void
}) {
  return (
    <div className="page-content simple-view">
      <p className="eyebrow accent-label"><Sparkles size={13} /> NEXORA / Saved</p>
      <h1>Your saved signals.</h1>
      <p className="hero-sub">Keep the ideas that deserve a second look close.</p>

      {savedItems.length === 0 ? (
        <div className="empty-note" style={{ marginTop: '48px' }}>
          <Layers3 size={18} />
          <div>
            <p className="text-sm font-medium">Nothing saved yet</p>
            <p className="text-xs text-muted-foreground">Bookmark recommendations from the Discover view.</p>
          </div>
        </div>
      ) : (
        <div className="recommendations-grid" style={{ marginTop: '32px' }}>
          {savedItems.map(item => (
            <RecommendationCard
              key={item.entity_id}
              item={item}
              liked={likedIds.has(item.entity_id)}
              saved={savedIds.has(item.entity_id)}
              onLike={() => onLike(item)}
              onSave={() => onSave(item)}
              onDislike={() => onDislike(item)}
              onWhy={() => onWhy(item)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Why Drawer ─────────────────────────────────────────────────────────────────
function WhyDrawer({ item, onClose }: { item: RecommendationItem; onClose: () => void }) {
  const wt = item.why_this
  const wn = item.why_now

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="why-drawer" onClick={e => e.stopPropagation()}>
        <button className="drawer-close" onClick={onClose} aria-label="Close explanation"><X size={18} /></button>
        <p className="eyebrow accent-label"><Sparkles size={13} /> Explainable intelligence</p>
        <h2>Why this signal?</h2>

        {wn && (
          <div style={{ marginTop: '12px', padding: '10px 12px', background: 'oklch(.76 .16 174 / .08)', borderRadius: '8px', fontSize: '12px', color: 'var(--primary)' }}>
            ⚡ {wn.text}
          </div>
        )}

        {item.reasons.length > 0 && (
          <div className="explain-list" style={{ marginTop: '20px' }}>
            {item.reasons.map((r, i) => (
              <div key={i}>
                <Check size={14} />
                <span>{r.text}</span>
                <strong>{Math.round(r.strength * 100)}%</strong>
              </div>
            ))}
          </div>
        )}

        {wt && (
          <>
            <div className="explain-score">
              <MatchRing score={item.match_percentage} />
              <div>
                <p className="text-sm font-medium">Relevance score</p>
                <p className="text-xs text-muted-foreground">Confidence: {item.confidence}</p>
              </div>
            </div>

            <div style={{ marginTop: '16px', fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '8px', color: 'var(--muted-foreground)' }}>
              {[
                ['Query match', wt.query_match],
                ['Profile match', wt.profile_match],
                ['Behaviour match', wt.behaviour_match],
                ['Rating', wt.rating_score],
              ].map(([label, val]) => (
                <div key={String(label)} className="flex items-center gap-2">
                  <span style={{ flex: 1 }}>{label}</span>
                  <div style={{ width: '80px', height: '4px', background: 'var(--border)', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{ width: `${Math.round(Number(val) * 100)}%`, height: '100%', background: 'var(--primary)', borderRadius: '2px' }} />
                  </div>
                  <span style={{ width: '36px', textAlign: 'right' }}>{(Number(val) * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>

            {wt.evidence.length > 0 && (
              <div style={{ marginTop: '16px', fontSize: '11px', color: 'var(--muted-foreground)' }}>
                <p style={{ marginBottom: '8px', fontWeight: 500, color: 'var(--foreground)' }}>Evidence</p>
                {wt.evidence.map((e, i) => <p key={i}>· {e}</p>)}
              </div>
            )}
          </>
        )}

        <button className="primary-button w-full" style={{ marginTop: '24px' }}>
          Keep exploring <ArrowUpRight size={15} />
        </button>
      </aside>
    </div>
  )
}

// ── Root page ──────────────────────────────────────────────────────────────────
export default function Page() {
  const [view, setView] = useState<View>('Discover')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [processing, setProcessing] = useState(false)
  const [why, setWhy] = useState<RecommendationItem | null>(null)

  // Stable IDs
  const userId = useRef<string>('')
  const sessionId = useRef<string>('')
  useEffect(() => {
    userId.current = getOrCreate('nexora_user_id', () => genId('usr'))
    sessionId.current = getOrCreate('nexora_session_id', () => genId('ses'))
  }, [])

  // Data state
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([])
  const [retrieval, setRetrieval] = useState<SearchResponse['retrieval'] | null>(null)
  const [profile, setProfile] = useState<ProfileSummary | null>(null)
  const [likedIds, setLikedIds] = useState<Set<string>>(new Set())
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set())
  const [savedItems, setSavedItems] = useState<RecommendationItem[]>([])
  const [sessionSignalCount, setSessionSignalCount] = useState(0)

  // Load profile for demo: pick a heavy user on first load
  useEffect(() => {
    // Try to load an interesting APS-04 user for demo personalization
    // In production the user would log in; here we auto-pick from APS-04
    listUsers('heavy', 1).then(data => {
      if (data.users.length > 0) {
        const uid = data.users[0].user_id as string
        userId.current = uid
        return getProfile(uid)
      }
      return null
    }).then(p => {
      if (p) setProfile(p)
    }).catch(() => {})
  }, [])

  const handleSearch = useCallback(async () => {
    if (!prompt.trim()) return
    setProcessing(true)
    try {
      const resp = await search({
        user_id: userId.current || undefined,
        session_id: sessionId.current || undefined,
        query: prompt,
        limit: 9,
      })
      setRecommendations(resp.results)
      setRetrieval(resp.retrieval)
      if (resp.profile) setProfile(resp.profile)
      if (resp.session) {
        setSessionSignalCount(Object.keys(resp.session.session_preferences).length)
      }
    } catch (e) {
      console.error('Search error:', e)
    } finally {
      setProcessing(false)
    }
  }, [prompt])

  const handleInteraction = useCallback(async (
    item: RecommendationItem,
    type: 'like' | 'save' | 'dislike' | 'click',
  ) => {
    if (!userId.current || !sessionId.current) return

    // Optimistic UI update
    if (type === 'like') {
      setLikedIds(prev => { const s = new Set(prev); s.has(item.entity_id) ? s.delete(item.entity_id) : s.add(item.entity_id); return s })
    } else if (type === 'save') {
      setSavedIds(prev => {
        const s = new Set(prev)
        if (s.has(item.entity_id)) {
          s.delete(item.entity_id)
          setSavedItems(si => si.filter(i => i.entity_id !== item.entity_id))
        } else {
          s.add(item.entity_id)
          setSavedItems(si => [...si, item])
        }
        return s
      })
    }

    try {
      const resp = await recordInteraction({
        user_id: userId.current,
        session_id: sessionId.current,
        entity_id: item.entity_id,
        entity_type: item.entity_type,
        interaction_type: type,
        position_in_list: item.rank,
        query_text: prompt || undefined,
      })

      if (resp.recorded) {
        // Update profile
        if (resp.session_update) {
          setSessionSignalCount(Object.keys(resp.session_update.session_preferences).length)
        }
        // Update recommendations with rank changes if backend re-ranked
        if (resp.recommendations.length > 0) {
          setRecommendations(resp.recommendations)
        }
        // Rebuild profile
        if (userId.current) {
          getProfile(userId.current).then(setProfile).catch(() => {})
        }
      }
    } catch (e) {
      console.error('Interaction error:', e)
    }
  }, [prompt])

  return (
    <main className="nexora-app">
      <Sidebar
        view={view}
        setView={setView}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
        savedCount={savedIds.size}
        profile={profile}
      />

      <div className="main-column">
        <Topbar
          setMobileOpen={setMobileOpen}
          prompt={prompt}
          setPrompt={setPrompt}
          onSubmit={handleSearch}
          profile={profile}
        />

        {view === 'Discover' && (
          <Discover
            prompt={prompt}
            setPrompt={setPrompt}
            processing={processing}
            onWhy={setWhy}
            recommendations={recommendations}
            retrieval={retrieval}
            onSearch={handleSearch}
            onLike={item => handleInteraction(item, 'like')}
            onSave={item => handleInteraction(item, 'save')}
            onDislike={item => handleInteraction(item, 'dislike')}
            likedIds={likedIds}
            savedIds={savedIds}
          />
        )}
        {view === 'For You' && (
          <Discover
            prompt={prompt}
            setPrompt={setPrompt}
            processing={processing}
            onWhy={setWhy}
            recommendations={recommendations}
            retrieval={retrieval}
            onSearch={handleSearch}
            onLike={item => handleInteraction(item, 'like')}
            onSave={item => handleInteraction(item, 'save')}
            onDislike={item => handleInteraction(item, 'dislike')}
            likedIds={likedIds}
            savedIds={savedIds}
          />
        )}
        {view === 'Saved' && (
          <SavedView
            savedItems={savedItems}
            onWhy={setWhy}
            likedIds={likedIds}
            savedIds={savedIds}
            onLike={item => handleInteraction(item, 'like')}
            onSave={item => handleInteraction(item, 'save')}
            onDislike={item => handleInteraction(item, 'dislike')}
          />
        )}
        {view === 'Profile' && <ProfileView profile={profile} />}
        {view === 'Evaluation' && <EvaluationView />}
        {view === 'System' && <SystemView />}
      </div>

      <Rail
        setView={setView}
        profile={profile}
        sessionSignalCount={sessionSignalCount}
      />

      {why && <WhyDrawer item={why} onClose={() => setWhy(null)} />}
    </main>
  )
}
