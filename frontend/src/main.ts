import './styles/portal.css';
import { PortalApp } from './portal-app';

document.addEventListener('DOMContentLoaded', () => {
  const headerEl = document.getElementById('portal-header');
  const mainEl = document.getElementById('portal-main');

  if (!headerEl || !mainEl) {
    console.error('FINXL Student Portal: Required DOM mount points (#portal-header, #portal-main) not found.');
    return;
  }

  const app = new PortalApp(headerEl, mainEl);
  app.showProgression();
});
