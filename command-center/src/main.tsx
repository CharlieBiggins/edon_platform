import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import Login from './Login';
import './styles.css';

function Root() {
  const [authenticated, setAuthenticated] = React.useState(() => window.sessionStorage.getItem('cerebrum.authenticated') === 'true');
  const authenticate = () => { window.sessionStorage.setItem('cerebrum.authenticated', 'true'); setAuthenticated(true); };
  return authenticated ? <App /> : <Login onAuthenticated={authenticate} />;
}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><Root /></React.StrictMode>);
