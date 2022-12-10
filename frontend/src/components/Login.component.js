import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Backdrop,
  Box,
  Button,
  Card,
  CardActions,
  FilledInput,
  FormControl,
  Grid,
  IconButton,
  InputAdornment,
  InputLabel,
  Snackbar
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { lightBlue } from '@mui/material/colors';
//import HiveRoundedIcon from '@mui/icons-material/HiveRounded';
import LoginIcon from '@mui/icons-material/Login';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import { apiUrl } from '../shared/Variables';
import Move from '../shared/Move';
import useToken from '../hooks/useToken';
import useUserData from '../hooks/useUserData';
import AnimatedAppLogo from './Animated-app-logo.component';

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

  const handleClickShowPassword = () => {
    setValues({
      ...values,
      showPassword: !values.showPassword
    });
  };

  const handleMouseDownPassword = (event) => {
    event.preventDefault();
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

  const LoginButton = styled(Button)(({ theme }) => ({
    color: theme.palette.getContrastText(lightBlue[600]),
    backgroundColor: lightBlue[700],
    '&:hover': {
      backgroundColor: lightBlue[500]
    }
  }));

  const SignupButton = styled(Button)(({ theme }) => ({
    color: theme.palette.getContrastText(lightBlue[600]),
    backgroundColor: lightBlue[700],
    '&:hover': {
      backgroundColor: lightBlue[500]
    }
  }));

  const [loginMessage, setLoginMessage] = useState('');
  const [openLoginStatus, setOpenLoginStatus] = useState(false);

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <Backdrop sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }} open={true}>
          <Card sx={{ minWidth: '40vh', minHeight: '20vh' }}>
            <Box display="flex" justifyContent="center" sx={{ paddingBottom: 1, paddingTop: 8 }}>
              <AnimatedAppLogo width={80} height={80} duration={1000} />
            </Box>
            <Grid item>
              <Box display="flex" justifyContent="center" alignItems="center">
                <FormControl sx={{ m: 2, width: '70%' }} variant="outlined">
                  <InputLabel htmlFor="email">Email</InputLabel>
                  <FilledInput
                    required
                    id="email"
                    type="email"
                    value={values.email}
                    onChange={handleChange('email')}
                    label="Email"
                  />
                </FormControl>
              </Box>
              <Box display="flex" justifyContent="center" alignItems="center">
                <FormControl sx={{ m: 2, width: '70%' }} variant="outlined">
                  <InputLabel htmlFor="password">Password</InputLabel>
                  <FilledInput
                    required
                    id="password"
                    type={values.showPassword ? 'text' : 'password'}
                    value={values.password}
                    onChange={handleChange('password')}
                    endAdornment={
                      <InputAdornment position="end">
                        <IconButton
                          aria-label="toggle password visibility"
                          onClick={handleClickShowPassword}
                          onMouseDown={handleMouseDownPassword}
                          edge="end">
                          {values.showPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    }
                    label="Password"
                  />
                </FormControl>
              </Box>
              <Grid item>
                <Box
                  display="flex"
                  justifyContent="center"
                  alignItem="center"
                  sx={{ paddingBottom: 2 }}>
                  <CardActions>
                    <FormControl>
                      <Box sx={{ display: 'flex', flexDirection: 'row', flexGrow: 1 }}>
                        <Move
                          rotation={0}
                          timing={1000}
                          scale={1.2}
                          springConfig={{ tension: 150, friction: 20 }}>
                          <LoginButton
                            size="large"
                            endIcon={<LoginIcon />}
                            type="submit"
                            sx={{ margin: 2 }}>
                            LOGIN
                          </LoginButton>
                        </Move>
                        <Move
                          rotation={0}
                          timing={1000}
                          scale={1.2}
                          springConfig={{ tension: 150, friction: 20 }}>
                          <SignupButton
                            disabled
                            size="large"
                            endIcon={<PersonAddIcon />}
                            onClick={() => console.log('sign up')}
                            sx={{ margin: 2 }}>
                            SIGN UP
                          </SignupButton>
                        </Move>
                      </Box>
                    </FormControl>
                  </CardActions>
                </Box>
              </Grid>
            </Grid>
          </Card>
        </Backdrop>
      </form>

      {openLoginStatus && (
        <Snackbar
          open={openLoginStatus}
          autoHideDuration={6000}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
          onClose={(event, reason) => {
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
