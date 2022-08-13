import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { ThemeProvider } from '@mui/material/styles';
import { keepTheme, setThemeParameters } from './hooks/setTheme';
import { CssBaseline } from '@mui/material';

import App from './App';
import Jobs from './job/View';
import Incidents from './incident/View';
import NotFoundPage from './components/404.component';
import OnCall from './pager/View';
import Settings from './settings/View';
import ViewSingleIncident from './incident/Single-incident';

import LoginPage from './components/Login.component';
import PersistentDrawerLeft from './components/AppDrawer.component';
import { PrivateRoute } from './shared/PrivateRoute';

import 'bootstrap/dist/css/bootstrap.css';
import './App.css';

import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(document.getElementById('root'));
keepTheme();
root.render(
  <React.StrictMode>
    <BrowserRouter basename="/app">
      <ThemeProvider theme={setThemeParameters()}>
        <CssBaseline />
        <PersistentDrawerLeft />
        <Routes>
          <Route
            path="/"
            element={
              <PrivateRoute>
                <App />
              </PrivateRoute>
            }
          />
          <Route
            path="/incidents"
            element={
              <PrivateRoute>
                <Incidents />
              </PrivateRoute>
            }
          />
          <Route
            path="/incidents/:incidentName"
            element={
              <PrivateRoute>
                <ViewSingleIncident />
              </PrivateRoute>
            }
          />
          <Route
            path="/on-call"
            element={
              <PrivateRoute>
                <OnCall />
              </PrivateRoute>
            }
          />
          <Route
            path="/jobs"
            element={
              <PrivateRoute>
                <Jobs />
              </PrivateRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <PrivateRoute>
                <Settings />
              </PrivateRoute>
            }
          />
          <Route path="/login" element={<LoginPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
