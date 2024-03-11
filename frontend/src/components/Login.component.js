import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Container,
  Link,
  Snackbar,
  TextField,
  Typography
} from '@mui/material';
import { apiUrl } from '../shared/Variables';

import CssBaseline from '@mui/material/CssBaseline';
import { createTheme, ThemeProvider } from '@mui/material/styles';

import AnimatedAppLogo from './Animated-app-logo.component';
import useToken from '../hooks/useToken';
import useUserData from '../hooks/useUserData';

const defaultTheme = createTheme();

function Copyright(props) {
  return (
    <Typography variant="body2" color="text.secondary" align="center" {...props}>
      <Link color="inherit" href="https://incidentbot.io/" target="new">
        incidentbot.io
      </Link>
    </Typography>
  );
}

async function loginUser(credentials) {
  return fetch(`${apiUrl}/user/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(credentials)
  }).then((data) => data.json());
}

const LoginPage = () => {
  const { setToken } = useToken();
  const { setUserData } = useUserData();

  let navigate = useNavigate();
  const [values, setValues] = useState({
    email: '',
    password: ''
  });

  const handleChange = (prop) => (event) => {
    setValues({ ...values, [prop]: event.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const token = await loginUser({
      email: `${values.email}`,
      password: `${values.password}`
    });
    if (!token.success) {
      setLoginMessage(token.error);
      setOpenLoginStatus(true);
    } else if (token.success) {
      setToken(token.access_token);
      setUserData(token.user_data);
      navigate('/');
    }
  };

  const [loginMessage, setLoginMessage] = useState('');
  const [openLoginStatus, setOpenLoginStatus] = useState(false);

  return (
    <div>
      <ThemeProvider theme={defaultTheme}>
        <Container component="main" maxWidth="xs">
          <CssBaseline />
          <Box
            sx={{
              marginTop: 8,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center'
            }}>
            <AnimatedAppLogo />
            <Typography component="h1" variant="h6" sx={{ margin: 1 }}>
              INCIDENT BOT
            </Typography>
            <Box component="form" onSubmit={handleSubmit} noValidate sx={{ mt: 1 }}>
              <TextField
                margin="normal"
                required
                fullWidth
                id="email"
                label="Email Address"
                name="email"
                autoComplete="email"
                autoFocus
                onChange={handleChange('email')}
              />
              <TextField
                margin="normal"
                required
                fullWidth
                name="password"
                label="Password"
                type="password"
                id="password"
                autoComplete="current-password"
                onChange={handleChange('password')}
              />
              <Button type="submit" fullWidth variant="contained" sx={{ mt: 3, mb: 2 }}>
                Sign In
              </Button>
            </Box>
          </Box>
          <Copyright sx={{ mt: 4, mb: 4 }} />
        </Container>
      </ThemeProvider>
      {openLoginStatus && (
        <Snackbar
          open={openLoginStatus}
          autoHideDuration={6000}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
          onClose={(reason) => {
            if (reason === 'clickaway') {
              return;
            }
            setOpenLoginStatus(false);
          }}>
          <Alert severity="error" variant="filled" sx={{ width: '100%' }}>
            {loginMessage}
          </Alert>
        </Snackbar>
      )}
    </div>
  );
};

export default LoginPage;
