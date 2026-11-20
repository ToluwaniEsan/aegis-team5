import React from 'react';
import ReactDOM from 'react-dom/client';
import '@fontsource/ibm-plex-sans/latin-400.css';
import '@fontsource/ibm-plex-sans/latin-600.css';
import '@fontsource/ibm-plex-mono/latin-400.css';
import '@fontsource/ibm-plex-mono/latin-600.css';
import './styles/tokens.css';
import './styles/base.css';
import { OperatorScreen } from './OperatorScreen';
import { MockFeed } from './mock/MockFeed';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {import.meta.env.VITE_MOCK === '1' ? <MockFeed><OperatorScreen /></MockFeed> : <OperatorScreen />}
  </React.StrictMode>,
);
