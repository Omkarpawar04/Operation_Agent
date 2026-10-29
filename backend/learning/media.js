import dns from 'dns/promises';
import net from 'net';

// What kind of link is a video? Only links the page can follow second by second count as "tracked".
//   youtube / vimeo: their players report the playing position
//   file: a direct .mp4/.webm file played in the browser's own player
//   other: anything else (Google Drive, a web page...). Cannot be tracked, so the student confirms it by hand.
const FILE = /\.(mp4|webm|ogv|ogg|mov|m4v)$/i;

export function youtubeId(u) {
  const host = u.hostname.replace(/^www\./, '');
  if (host === 'youtu.be') return u.pathname.slice(1).split('/')[0] || null;
  if (host.endsWith('youtube.com') || host.endsWith('youtube-nocookie.com')) {
    if (u.pathname === '/watch') return u.searchParams.get('v');
    const m = u.pathname.match(/^\/(?:embed|shorts|live)\/([\w-]+)/);
    if (m) return m[1];
  }
  return null;
}

export function vimeoId(u) {
  const host = u.hostname.replace(/^www\./, '');
  if (host !== 'vimeo.com' && !host.endsWith('.vimeo.com')) return null;
  const m = u.pathname.match(/\/(\d{5,})/);
  return m ? m[1] : null;
}

export function providerOf(url) {
  try {
    const u = new URL(url);
    if (youtubeId(u)) return 'youtube';
    if (vimeoId(u)) return 'vimeo';
    if (FILE.test(u.pathname)) return 'file';
  } catch { /* not a link */ }
  return 'other';
}

const isPrivateIp = (ip) => {
  if (net.isIPv4(ip)) {
    const [a, b] = ip.split('.').map(Number);
    return a === 0 || a === 10 || a === 127 || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || a >= 224;
  }
  const l = ip.toLowerCase();
  return l === '::1' || l === '::' || l.startsWith('fc') || l.startsWith('fd') || l.startsWith('fe80') || l.startsWith('::ffff:');
};

// The streaming proxy fetches a link on the student's behalf, so it must never reach into the server's own network.
// STREAM_ALLOW_PRIVATE=true switches the check off (for local testing only).
export async function assertPublicHost(hostname) {
  if (process.env.STREAM_ALLOW_PRIVATE === 'true') return;
  const found = net.isIP(hostname) ? [{ address: hostname }] : await dns.lookup(hostname, { all: true });
  if (!found.length || found.some((a) => isPrivateIp(a.address))) throw new Error('That address is not allowed');
}
