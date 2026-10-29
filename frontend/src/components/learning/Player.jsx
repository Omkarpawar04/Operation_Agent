import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, ExternalLink } from 'lucide-react';
import { API_BASE } from '../../api.js';
import { otherEmbed, parseVideo } from './shared.jsx';

// A video player that reports what the student really watched.
//  - YouTube and Vimeo use their own player scripts, a direct file uses the browser's <video>.
//  - Every second actually played is collected and sent every few seconds (and on pause / leaving the page).
//  - Jumping ahead is not counted; the server also limits how fast seconds can be claimed.
// onBeat(ranges, position, duration) sends the batch and returns the server's answer.

class Tracker {
  constructor(send) {
    this.send = send; this.pending = new Set(); this.last = null; this.duration = 0; this.position = 0;
    this.sending = false; this.again = false;
    this.timer = setInterval(() => this.flush(), 8000);
    this.onHide = () => { if (document.visibilityState === 'hidden') this.flush(); };
    document.addEventListener('visibilitychange', this.onHide);
  }

  // Called while the video plays, with the current position. A small step forward counts every second passed;
  // a jump (seek) counts only where playing continues from.
  time(t, d) {
    if (Number.isFinite(d) && d > 0) this.duration = d;
    if (!Number.isFinite(t)) return;
    this.position = t;
    if (this.last !== null && t >= this.last && t - this.last <= 3) for (let s = Math.floor(this.last); s <= Math.floor(t); s += 1) this.pending.add(s);
    else this.pending.add(Math.floor(t));
    this.last = t;
  }

  stop() { this.last = null; this.flush(); }

  async flush() {
    if (!this.pending.size || !this.duration) return;
    if (this.sending) { this.again = true; return; }
    const secs = [...this.pending].sort((a, b) => a - b);
    this.pending = new Set();
    const ranges = [];
    for (const s of secs) {
      const r = ranges[ranges.length - 1];
      if (r && s === r[1] + 1 && s - r[0] < 600) r[1] = s; else ranges.push([s, s]);
    }
    this.sending = true;
    try { await this.send(ranges.slice(0, 60), Math.floor(this.position), this.duration); }
    catch { secs.forEach((s) => this.pending.add(s)); } // try again on the next round
    finally { this.sending = false; if (this.again) { this.again = false; this.flush(); } }
  }

  destroy() { clearInterval(this.timer); document.removeEventListener('visibilitychange', this.onHide); this.last = null; this.flush(); }
}

// Start where the student stopped, unless that was the very end
const resumeAt = (info) => (info.position > 0 && (!info.duration_sec || info.position < info.duration_sec - 5) ? Math.floor(info.position) : 0);

const once = (key, start) => { if (!window.__players) window.__players = {}; if (!window.__players[key]) window.__players[key] = start(); return window.__players[key]; };
const loadYouTube = () => once('yt', () => new Promise((resolve, reject) => {
  if (window.YT?.Player) return resolve(window.YT);
  const prev = window.onYouTubeIframeAPIReady;
  window.onYouTubeIframeAPIReady = () => { prev?.(); resolve(window.YT); };
  const s = document.createElement('script');
  s.src = 'https://www.youtube.com/iframe_api'; s.onerror = () => { window.__players.yt = null; reject(new Error('blocked')); };
  document.head.appendChild(s);
}));
const loadVimeo = () => once('vimeo', () => new Promise((resolve, reject) => {
  if (window.Vimeo?.Player) return resolve(window.Vimeo);
  const s = document.createElement('script');
  s.src = 'https://player.vimeo.com/api/player.js'; s.onload = () => resolve(window.Vimeo); s.onerror = () => { window.__players.vimeo = null; reject(new Error('blocked')); };
  document.head.appendChild(s);
}));

function Problem({ children, link }) {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-white text-center p-6 bg-gradient-to-br from-slate-900 to-slate-800">
      <AlertCircle size={32} className="text-amber-400" />
      <p className="text-sm max-w-md">{children}</p>
      {link && <a href={link} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 text-xs font-bold bg-white/15 hover:bg-white/25 rounded-xl px-4 py-2"><ExternalLink size={14} /> Open the video in a new tab</a>}
    </div>
  );
}

function YouTubePlayer({ id, info, beat, url }) {
  const host = useRef(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    let dead = false; let player = null; let poll = null;
    const tracker = new Tracker((...a) => beat.current(...a));
    loadYouTube().then((YT) => {
      if (dead || !host.current) return;
      const el = document.createElement('div'); host.current.appendChild(el);
      player = new YT.Player(el, {
        width: '100%', height: '100%', videoId: id,
        playerVars: { start: resumeAt(info), rel: 0, modestbranding: 1, playsinline: 1, origin: window.location.origin },
        events: {
          onStateChange: (e) => { if (e.data === 2 || e.data === 0) tracker.stop(); else if (e.data === 1) tracker.last = null; },
          onError: () => setErr('YouTube would not play this video here. The owner may have switched off embedding.'),
        },
      });
      poll = setInterval(() => { try { if (player.getPlayerState?.() === 1) tracker.time(player.getCurrentTime(), player.getDuration()); } catch { /* player not ready */ } }, 1000);
    }).catch(() => setErr('The YouTube player could not load. Check your internet connection or ad blocker.'));
    return () => { dead = true; clearInterval(poll); tracker.destroy(); try { player?.destroy(); } catch { /* already gone */ } if (host.current) host.current.innerHTML = ''; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);
  return <><div ref={host} className="absolute inset-0 [&>iframe]:w-full [&>iframe]:h-full" data-player="youtube" />{err && <Problem link={url}>{err}</Problem>}</>;
}

function VimeoPlayer({ info, beat, url }) {
  const host = useRef(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    let dead = false; let player = null;
    const tracker = new Tracker((...a) => beat.current(...a));
    loadVimeo().then((Vimeo) => {
      if (dead || !host.current) return;
      player = new Vimeo.Player(host.current, { url: info.video_url, responsive: true });
      player.on('timeupdate', (d) => tracker.time(d.seconds, d.duration));
      player.on('play', () => { tracker.last = null; });
      player.on('pause', () => tracker.stop());
      player.on('ended', () => tracker.stop());
      player.ready().then(() => { const at = resumeAt(info); if (at) player.setCurrentTime(at).catch(() => {}); }).catch(() => setErr('Vimeo would not play this video here.'));
    }).catch(() => setErr('The Vimeo player could not load. Check your internet connection or ad blocker.'));
    return () => { dead = true; tracker.destroy(); try { player?.destroy(); } catch { /* already gone */ } if (host.current) host.current.innerHTML = ''; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [info.video_url]);
  return <><div ref={host} className="absolute inset-0 flex items-center [&>div]:w-full" data-player="vimeo" />{err && <Problem link={url}>{err}</Problem>}</>;
}

// A direct video file. Some file hosts forbid other websites from playing their files; the browser then refuses it,
// and the player switches to the backend's stream, which has no such limit.
function FilePlayer({ videoId, info, beat }) {
  const ref = useRef(null);
  const [src, setSrc] = useState(info.video_url);
  const [via, setVia] = useState('direct');
  const [err, setErr] = useState('');

  useEffect(() => {
    const v = ref.current;
    if (!v) return undefined;
    const tracker = new Tracker((...a) => beat.current(...a));
    const onTime = () => { if (!v.paused && !v.seeking) tracker.time(v.currentTime, v.duration); };
    const onMeta = () => { const at = resumeAt({ ...info, duration_sec: v.duration }); if (at) v.currentTime = at; };
    const stop = () => tracker.stop();
    const resetLast = () => { tracker.last = null; };
    v.addEventListener('timeupdate', onTime); v.addEventListener('loadedmetadata', onMeta);
    v.addEventListener('pause', stop); v.addEventListener('ended', stop); v.addEventListener('seeking', resetLast); v.addEventListener('play', resetLast);
    return () => {
      ['timeupdate', 'loadedmetadata', 'pause', 'ended', 'seeking', 'play'].forEach((n, i) => v.removeEventListener(n, [onTime, onMeta, stop, stop, resetLast, resetLast][i]));
      tracker.destroy();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [src]);

  const failed = () => {
    if (via === 'direct') { setVia('stream'); setSrc(`${API_BASE}/learning/videos/${videoId}/stream?token=${encodeURIComponent(info.stream_token)}`); }
    else setErr('This video file could not be played. Ask your trainer to check the link.');
  };
  return (
    <>
      <video key={src} ref={ref} src={src} controls controlsList="nodownload" playsInline preload="metadata" onError={failed} className="absolute inset-0 w-full h-full bg-black" data-player="file" data-via={via} />
      {err && <Problem>{err}</Problem>}
    </>
  );
}

export default function Player({ videoId, info, onBeat }) {
  const beat = useRef(onBeat);
  beat.current = onBeat;
  const parsed = parseVideo(info.video_url);
  const drive = parsed.provider === 'other' ? otherEmbed(info.video_url) : null;
  return (
    <div className="relative bg-black aspect-video" aria-label="Video player" data-provider={parsed.provider}>
      {parsed.provider === 'youtube' && <YouTubePlayer key={videoId} id={parsed.id} info={info} beat={beat} url={info.video_url} />}
      {parsed.provider === 'vimeo' && <VimeoPlayer key={videoId} info={info} beat={beat} url={info.video_url} />}
      {parsed.provider === 'file' && <FilePlayer key={videoId} videoId={videoId} info={info} beat={beat} />}
      {parsed.provider === 'other' && (drive
        ? <iframe key={videoId} title="Lesson video" src={drive} className="absolute inset-0 w-full h-full" allow="autoplay" allowFullScreen />
        : <Problem link={info.video_url}>This link opens on another website. Watch it there, then come back and confirm below.</Problem>)}
    </div>
  );
}
