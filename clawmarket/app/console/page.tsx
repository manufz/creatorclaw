'use client'

import { useAuth } from '@/components/AuthProvider'
import { useEffect, useState, useRef, Suspense } from 'react'
import { CompanionCard } from '@/components/CompanionCard'
import Link from 'next/link'
import Image from 'next/image'
import { useSearchParams } from 'next/navigation'
import { bots } from '@/lib/bots'

// Role → what this bot is actively doing when running
const ROLE_ACTIVITY: Record<string, string[]> = {
  'CREATIVE DIRECTOR':   ['Defining visual concepts', 'Setting brand direction', 'Building mood boards', 'Reviewing creative briefs'],
  'COMIC BOOK WRITER':   ['Scripting panel descriptions', 'Building story arcs', 'Writing character dialogue', 'Drafting scene layouts'],
  'CONTENT WRITER':      ['Writing Instagram captions', 'Drafting blog post outlines', 'Generating video scripts', 'Crafting ad copy'],
  'AI VIDEO GENERATOR':  ['Generating video concepts', 'Building storyboards', 'Writing AI video prompts', 'Planning shot sequences'],
  'FILMMAKER':           ['Planning shoot scripts', 'Directing scene breakdowns', 'Writing cinematography notes', 'Reviewing edit decisions'],
  'DIGITAL ARTIST':      ['Generating art prompts', 'Defining style guides', 'Creating visual references', 'Building prompt libraries'],
  'POSTING ASSISTANT':   ['Scheduling content calendar', 'Writing platform captions', 'Optimising posting times', 'Drafting story scripts'],
  'VIDEO EDITOR':        ['Advising on cut decisions', 'Suggesting color grades', 'Reviewing pacing notes', 'Optimising for platform'],
  'MUSIC PRODUCER':      ['Building track briefs', 'Writing chord progressions', 'Structuring song outlines', 'Directing sonic identity'],
}

function getActivity(role: string | null): string {
  if (!role) return 'Processing requests'
  const list = ROLE_ACTIVITY[role.toUpperCase()]
  if (!list) return 'Processing requests'
  // rotate based on current minute so it "changes" over time
  return list[Math.floor(Date.now() / 60000) % list.length]
}

function getUptime(createdAt: string): string {
  const diff = Date.now() - new Date(createdAt).getTime()
  const days = Math.floor(diff / 86400000)
  const hours = Math.floor((diff % 86400000) / 3600000)
  const mins = Math.floor((diff % 3600000) / 60000)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}

export default function ConsolePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-white flex items-center justify-center pt-16">
        <div className="animate-spin h-8 w-8 border-3 border-brand-yellow border-t-transparent rounded-full mx-auto" />
      </div>
    }>
      <ConsoleContent />
    </Suspense>
  )
}

function ConsoleContent() {
  const { user, session, loading } = useAuth()
  const [instances, setInstances] = useState<any[]>([])
  const [subscription, setSubscription] = useState<any>(null)
  const [fetching, setFetching] = useState(true)
  const [fulfilling, setFulfilling] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'bots' | 'billing'>('overview')
  const [tick, setTick] = useState(0)
  const searchParams = useSearchParams()
  const sessionId = searchParams.get('session_id')
  const fulfilledRef = useRef(false)

  // Tick every 30s to rotate activity text
  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 30000)
    return () => clearInterval(iv)
  }, [])

  const fetchInstances = async () => {
    if (!session?.access_token) return
    try {
      const res = await fetch('/api/instance', {
        headers: { Authorization: `Bearer ${session.access_token}` },
      })
      const data = await res.json()
      setInstances(data.instances || [])
      setSubscription(data.subscription || null)
    } catch (err) {
      console.error('Error fetching instances:', err)
    } finally {
      setFetching(false)
    }
  }

  useEffect(() => {
    if (!sessionId || !session?.access_token || fulfilledRef.current) return
    fulfilledRef.current = true
    setFulfilling(true)
    fetch('/api/fulfill', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session.access_token}` },
      body: JSON.stringify({ session_id: sessionId }),
    })
      .then(async r => { const d = await r.json(); if (!r.ok) console.error('Fulfill error:', d.error); return d })
      .then(() => { window.history.replaceState({}, '', '/console'); fetchInstances() })
      .catch(err => console.error('Fulfill error:', err))
      .finally(() => setFulfilling(false))
  }, [sessionId, session])

  useEffect(() => { if (session) fetchInstances() }, [session])
  useEffect(() => {
    if (!session) return
    const interval = setInterval(fetchInstances, 15000)
    return () => clearInterval(interval)
  }, [session])

  const handleAction = async (instanceId: string, action: 'start' | 'stop' | 'terminate') => {
    setActionLoading(instanceId)
    try {
      const method = action === 'terminate' ? 'DELETE' : 'PATCH'
      const res = await fetch('/api/instance', {
        method,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session?.access_token}` },
        body: JSON.stringify({ action, instance_id: instanceId }),
      })
      if (!res.ok) { const data = await res.json(); alert(data.error || `Failed to ${action}`) }
      await fetchInstances()
    } catch (err) { console.error(`Error ${action}ing:`, err) }
    finally { setActionLoading(null) }
  }

  if (loading || fetching || fulfilling) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center pt-16">
        <div className="text-center">
          <div className="animate-spin h-8 w-8 border-3 border-brand-yellow border-t-transparent rounded-full mx-auto mb-4" />
          {fulfilling && <p className="text-brand-gray-medium font-display font-bold text-sm">Setting up your creator bot...</p>}
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center pt-16">
        <div className="text-center">
          <h2 className="comic-heading text-2xl mb-4">Sign in to view dashboard</h2>
          <Link href="/login" className="comic-btn inline-block">SIGN IN</Link>
        </div>
      </div>
    )
  }

  const running = instances.filter(i => i.status === 'running')
  const stopped = instances.filter(i => i.status === 'stopped')
  const deploying = instances.filter(i => ['provisioning', 'pending_payment'].includes(i.status))
  const monthlyCost = instances.filter(i => !['terminated'].includes(i.status)).length * 40

  // Bots NOT yet deployed by user
  const deployedBotIds = instances.map(i => i.bot_id || '').filter(Boolean)
  const recommendedBots = bots.filter(b => !deployedBotIds.includes(b.id)).slice(0, 3)

  return (
    <div className="min-h-screen bg-white pt-16">

      {/* Dashboard Header */}
      <div className="border-b-3 border-black bg-brand-yellow px-4 py-5">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-display font-black text-xs uppercase tracking-widest text-black/50">OpenClaw</span>
                <span className="text-black/30">/</span>
                <span className="font-display font-black text-xs uppercase tracking-widest">Dashboard</span>
              </div>
              <h1 className="comic-heading text-2xl md:text-3xl">YOUR CREATOR STUDIO</h1>
              <p className="text-sm font-body mt-0.5 text-black/60">
                {user.email || user.phone} &mdash; {instances.length} bot{instances.length !== 1 ? 's' : ''} deployed
              </p>
            </div>
            <div className="flex gap-2">
              <Link href="/companions" className="comic-btn text-sm py-2 px-4">
                + DEPLOY BOT
              </Link>
              <Link href="/create" className="comic-btn-outline bg-white text-sm py-2 px-4">
                BUILD BOT
              </Link>
            </div>
          </div>

          {/* Tab Nav */}
          <div className="flex gap-1 mt-5 -mb-5 border-t-2 border-black/20 pt-3">
            {(['overview', 'bots', 'billing'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-1.5 font-display font-bold text-xs uppercase border-2 border-black transition-all ${
                  activeTab === tab
                    ? 'bg-black text-white'
                    : 'bg-white/60 text-black hover:bg-white'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8">

        {/* ───────────── OVERVIEW TAB ───────────── */}
        {activeTab === 'overview' && (
          <div className="space-y-8">

            {/* Stats strip */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                {
                  label: 'Active Bots',
                  value: running.length,
                  icon: '🟢',
                  sub: 'running right now',
                  accent: 'border-green-400 bg-green-50',
                },
                {
                  label: 'Deploying',
                  value: deploying.length,
                  icon: '🟡',
                  sub: 'being set up',
                  accent: 'border-yellow-400 bg-yellow-50',
                },
                {
                  label: 'Stopped',
                  value: stopped.length,
                  icon: '⚫',
                  sub: 'paused',
                  accent: 'border-gray-300 bg-gray-50',
                },
                {
                  label: 'Monthly Cost',
                  value: `$${monthlyCost}`,
                  icon: '💰',
                  sub: `${instances.filter(i => i.status !== 'terminated').length} × $40`,
                  accent: 'border-brand-yellow bg-yellow-50',
                },
              ].map((stat) => (
                <div key={stat.label} className={`comic-card p-5 border-3 ${stat.accent}`}>
                  <div className="text-2xl mb-1">{stat.icon}</div>
                  <div className="comic-heading text-3xl">{stat.value}</div>
                  <div className="font-display font-bold text-xs uppercase mt-1">{stat.label}</div>
                  <div className="text-[11px] text-brand-gray-medium mt-0.5">{stat.sub}</div>
                </div>
              ))}
            </div>

            {/* Live Bot Activity */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="comic-heading text-xl">WHAT YOUR BOTS ARE DOING</h2>
                <div className="flex items-center gap-1.5 text-[11px] font-display font-bold text-green-600 uppercase">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  Live
                </div>
              </div>

              {instances.length === 0 ? (
                <div className="comic-card p-10 text-center border-dashed">
                  <div className="text-5xl mb-4">🎨</div>
                  <h3 className="comic-heading text-xl mb-2">NO BOTS DEPLOYED YET</h3>
                  <p className="text-brand-gray-medium font-body mb-5 max-w-sm mx-auto">
                    Deploy your first AI creator bot and see it working here in real time.
                  </p>
                  <Link href="/companions" className="comic-btn inline-block text-sm">
                    EXPLORE CREATOR BOTS
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  {instances.map(instance => {
                    const color = instance.companion_color || '#FFD600'
                    const isRunning = instance.status === 'running'
                    const isStopped = instance.status === 'stopped'
                    const isDeploying = ['provisioning', 'pending_payment'].includes(instance.status)
                    const isFailed = ['failed', 'payment_failed'].includes(instance.status)
                    const activity = getActivity(instance.companion_role)
                    const uptime = getUptime(instance.created_at)

                    return (
                      <div key={instance.id} className="comic-card overflow-hidden">
                        <div className="h-1.5" style={{ backgroundColor: color }} />
                        <div className="p-4 flex flex-col sm:flex-row sm:items-center gap-4">

                          {/* Avatar + Name */}
                          <div className="flex items-center gap-3 min-w-0 flex-1">
                            <div
                              className="w-12 h-12 rounded-full border-3 border-black flex-shrink-0 overflow-hidden flex items-center justify-center"
                              style={{ backgroundColor: `${color}25` }}
                            >
                              {instance.companion_avatar ? (
                                <Image src={instance.companion_avatar} alt="" width={48} height={48} className="w-full h-full object-cover" />
                              ) : (
                                <span className="font-display font-black text-lg" style={{ color }}>
                                  {(instance.companion_name || '?').charAt(0)}
                                </span>
                              )}
                            </div>
                            <div className="min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-display font-black text-base uppercase">
                                  {instance.companion_name || 'Bot'}
                                </span>
                                <span
                                  className="text-[10px] font-display font-bold uppercase px-2 py-0.5 border-2 border-black"
                                  style={{ backgroundColor: `${color}30` }}
                                >
                                  {instance.companion_role || 'Creator Bot'}
                                </span>
                              </div>
                              {/* Activity line */}
                              <div className="flex items-center gap-1.5 mt-1">
                                {isRunning && (
                                  <>
                                    <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse flex-shrink-0" />
                                    <span className="text-xs text-green-700 font-body italic truncate">
                                      {activity}...
                                    </span>
                                  </>
                                )}
                                {isStopped && (
                                  <>
                                    <div className="w-1.5 h-1.5 rounded-full bg-gray-400 flex-shrink-0" />
                                    <span className="text-xs text-gray-500 font-body">Idle — stopped</span>
                                  </>
                                )}
                                {isDeploying && (
                                  <>
                                    <div className="w-1.5 h-1.5 rounded-full bg-yellow-500 animate-pulse flex-shrink-0" />
                                    <span className="text-xs text-yellow-700 font-body">Deploying to server...</span>
                                  </>
                                )}
                                {isFailed && (
                                  <>
                                    <div className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" />
                                    <span className="text-xs text-red-600 font-body">Deployment failed</span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Meta chips */}
                          <div className="flex flex-wrap items-center gap-2 flex-shrink-0">
                            <Chip icon="⚡" label={instance.model_name ? instance.model_name.split('/').pop()! : 'N/A'} />
                            <Chip icon="📡" label={instance.channel || 'telegram'} />
                            <Chip icon="⏱" label={`Up ${uptime}`} />
                            <Chip
                              icon={isRunning ? '🟢' : isStopped ? '⚫' : isDeploying ? '🟡' : '🔴'}
                              label={isRunning ? 'Online' : isStopped ? 'Stopped' : isDeploying ? 'Deploying' : 'Failed'}
                              highlight={isRunning}
                            />
                          </div>

                          {/* Quick actions */}
                          <div className="flex gap-2 flex-shrink-0">
                            {isRunning && instance.public_ip && (
                              <a
                                href={`http://${instance.public_ip}:8080?token=${instance.gateway_token}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="comic-btn text-xs py-1.5 px-3"
                              >
                                OPEN UI
                              </a>
                            )}
                            <button
                              onClick={() => setActiveTab('bots')}
                              className="comic-btn-outline text-xs py-1.5 px-3"
                            >
                              MANAGE
                            </button>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Creator Crew Progress */}
            {instances.length > 0 && instances.length < 9 && (
              <div className="comic-card p-6 bg-brand-yellow/10 border-brand-yellow">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <h3 className="comic-heading text-lg mb-1">YOUR CREATOR CREW</h3>
                    <p className="text-sm font-body text-brand-gray-dark">
                      {instances.length} of 9 creator bots deployed. Unlock the full studio.
                    </p>
                  </div>
                  <Link href="/company-package" className="comic-btn text-xs py-1.5 px-3 whitespace-nowrap">
                    GET CREATOR PACK
                  </Link>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {bots.map(bot => {
                    const deployed = instances.some(i =>
                      (i.companion_name || '').toLowerCase() === bot.characterName.toLowerCase()
                    )
                    return (
                      <div
                        key={bot.id}
                        className={`relative flex flex-col items-center gap-1 ${deployed ? 'opacity-100' : 'opacity-30'}`}
                        title={`${bot.characterName} — ${bot.characterRole}`}
                      >
                        <div
                          className="w-10 h-10 rounded-full border-3 border-black overflow-hidden"
                          style={{ backgroundColor: `${bot.color}30` }}
                        >
                          <Image src={bot.avatar} alt={bot.characterName} width={40} height={40} className="w-full h-full object-cover" />
                        </div>
                        {deployed && (
                          <div className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-green-500 rounded-full border-2 border-white" />
                        )}
                        <span className="text-[9px] font-display font-bold uppercase">{bot.characterName}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Suggest bots to deploy */}
            {recommendedBots.length > 0 && (
              <div>
                <h2 className="comic-heading text-xl mb-4">ADD TO YOUR CREW</h2>
                <div className="grid sm:grid-cols-3 gap-4">
                  {recommendedBots.map(bot => (
                    <div key={bot.id} className="comic-card-hover flex flex-col overflow-hidden">
                      <div className="h-1.5" style={{ backgroundColor: bot.color }} />
                      <div className="p-4 flex items-center gap-3">
                        <Image src={bot.avatar} alt={bot.characterName} width={48} height={48} className="avatar-comic rounded-full bg-brand-gray flex-shrink-0" />
                        <div className="min-w-0 flex-1">
                          <div className="font-display font-black text-sm uppercase">{bot.characterName}</div>
                          <div className="text-[10px] font-display font-bold uppercase text-brand-gray-medium mt-0.5">{bot.characterRole}</div>
                          <div className="text-[11px] font-body text-brand-gray-dark mt-1 line-clamp-1">{bot.tagline}</div>
                        </div>
                      </div>
                      <div className="px-4 pb-4 mt-auto">
                        <Link href={`/deploy?model=${bot.id}`} className="comic-btn block text-center text-xs w-full">
                          DEPLOY — $40/MO
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ───────────── BOTS TAB ───────────── */}
        {activeTab === 'bots' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="comic-heading text-xl">YOUR DEPLOYED BOTS</h2>
              <Link href="/companions" className="comic-btn text-sm py-2 px-4">+ DEPLOY NEW</Link>
            </div>

            {instances.length === 0 ? (
              <div className="comic-card p-10 text-center border-dashed">
                <div className="text-5xl mb-4">🎨</div>
                <h3 className="comic-heading text-xl mb-2">NO BOTS YET</h3>
                <p className="text-brand-gray-medium font-body mb-5">Deploy your first AI creator bot to get started.</p>
                <Link href="/companions" className="comic-btn inline-block text-sm">EXPLORE CREATOR BOTS</Link>
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {instances.map(instance => (
                  <CompanionCard
                    key={instance.id}
                    instance={instance}
                    onAction={handleAction}
                    onRefresh={fetchInstances}
                    actionLoading={actionLoading}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* ───────────── BILLING TAB ───────────── */}
        {activeTab === 'billing' && (
          <div className="space-y-6 max-w-2xl">
            <h2 className="comic-heading text-xl">BILLING & SUBSCRIPTION</h2>

            {/* Cost breakdown */}
            <div className="comic-card p-6">
              <h3 className="font-display font-bold text-sm uppercase mb-4">MONTHLY BREAKDOWN</h3>
              {instances.filter(i => i.status !== 'terminated').length === 0 ? (
                <p className="text-brand-gray-medium font-body text-sm">No active subscriptions.</p>
              ) : (
                <>
                  <div className="space-y-2 mb-4">
                    {instances.filter(i => i.status !== 'terminated').map(instance => (
                      <div key={instance.id} className="flex items-center justify-between py-2 border-b border-gray-100">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: instance.companion_color || '#FFD600' }} />
                          <span className="font-display font-bold text-sm uppercase">{instance.companion_name || 'Bot'}</span>
                          <span className="text-[10px] text-brand-gray-medium font-body">{instance.companion_role}</span>
                        </div>
                        <span className="font-display font-bold text-sm">$40/mo</span>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t-3 border-black">
                    <span className="font-display font-black text-sm uppercase">Total</span>
                    <span className="comic-heading text-2xl text-brand-yellow">${monthlyCost}<span className="text-base text-brand-gray-medium">/mo</span></span>
                  </div>
                </>
              )}
            </div>

            {/* Subscription status */}
            {subscription && (
              <div className="comic-card p-6">
                <h3 className="font-display font-bold text-sm uppercase mb-4">SUBSCRIPTION STATUS</h3>
                <div className="grid grid-cols-2 gap-4 mb-5">
                  <div>
                    <div className="text-[10px] text-brand-gray-medium font-display font-bold uppercase mb-1">Status</div>
                    <div className="text-sm text-black font-bold capitalize">
                      {subscription.status === 'trialing' ? '3-Day Free Trial' : subscription.status}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-brand-gray-medium font-display font-bold uppercase mb-1">
                      {subscription.status === 'trialing' ? 'Trial ends' : 'Next renewal'}
                    </div>
                    <div className="text-sm text-black">
                      {subscription.current_period_end
                        ? new Date(subscription.current_period_end).toLocaleDateString()
                        : 'N/A'}
                    </div>
                  </div>
                </div>
                <button
                  onClick={async () => {
                    const res = await fetch('/api/billing', { method: 'POST', headers: { Authorization: `Bearer ${session?.access_token}` } })
                    const data = await res.json()
                    if (data.url) window.location.href = data.url
                  }}
                  className="comic-btn-outline text-sm"
                >
                  MANAGE BILLING
                </button>
              </div>
            )}

            {/* Creator pack upsell */}
            {instances.length > 0 && instances.length < 9 && (
              <div className="comic-card p-6 bg-black text-white">
                <div className="font-display font-black text-xs uppercase text-brand-yellow mb-2">Save Money</div>
                <h3 className="comic-heading text-xl mb-2 text-white">UPGRADE TO CREATOR PACK</h3>
                <p className="text-sm text-gray-400 font-body mb-4">
                  Get all 9 creator bots for $300/mo instead of ${9 * 40}/mo. Save $60 every month.
                </p>
                <Link href="/company-package" className="comic-btn inline-block text-sm">
                  SEE CREATOR PACK
                </Link>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}

function Chip({ icon, label, highlight }: { icon: string; label: string; highlight?: boolean }) {
  return (
    <div className={`flex items-center gap-1 px-2 py-1 border-2 border-black text-[10px] font-display font-bold uppercase ${highlight ? 'bg-green-100' : 'bg-gray-50'}`}>
      <span>{icon}</span>
      <span className="truncate max-w-[80px]">{label}</span>
    </div>
  )
}
