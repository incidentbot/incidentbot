import React, { useState } from 'react';
import useToken from '../../../hooks/useToken';
import {
  Alert,
  Button,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputAdornment,
  InputLabel,
  MenuItem,
  OutlinedInput,
  Snackbar
} from '@mui/material';

import { styled } from '@mui/material/styles';
import { lightBlue } from '@mui/material/colors';

import PersonAddAltIcon from '@mui/icons-material/PersonAddAlt';
import SettingsIcon from '@mui/icons-material/Settings';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';

export default function PasswordChangeModal(props) {
  const { token } = useToken();

  const [values, setValues] = useState({
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

  const CreateUserButton = styled(Button)(({ theme }) => ({
    color: theme.palette.getContrastText(lightBlue[600]),
    backgroundColor: lightBlue[700],
    '&:hover': {
      backgroundColor: lightBlue[500]
    }
  }));

  const [open, setOpen] = useState(false);
  const handleOpen = () => setOpen(true);
  const handleClose = () => setOpen(false);

  const [resetPasswordStatus, setResetPasswordStatus] = useState('');
  const [resetPasswordMessage, setResetPasswordMessage] = useState('');
  const [openResetPasswordStatus, setOpenResetPasswordStatus] = useState(false);

  async function userPasswordReset(values) {
    return fetch(`${props.apiUrl}/user/${props.user.id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + token
      },
      body: JSON.stringify({ field: 'change_password', password: values.password })
    }).then((data) => data.json());
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    const user = await userPasswordReset({
      password: `${values.password}`
    });
    if (!user.success) {
      setResetPasswordStatus('error');
      setResetPasswordMessage(`Error changing password: ${user.error}`);
      setOpenResetPasswordStatus(true);
    } else if (user.success) {
      setResetPasswordStatus('success');
      setResetPasswordMessage('Password changed successfully!');
      setOpenResetPasswordStatus(true);
      setOpen(false);
    }
  };

  return (
    <div>
      <MenuItem onClick={handleOpen} variant="contained" endIcon={<SettingsIcon />}>
        Change Password
      </MenuItem>
      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit}>
          <DialogTitle>Change Password</DialogTitle>
          <DialogContent>Enter new password</DialogContent>
          <DialogContent>
            <FormControl variant="outlined" fullWidth sx={{ marginBottom: 2 }}>
              <InputLabel htmlFor="password">Password</InputLabel>
              <OutlinedInput
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
          </DialogContent>
          <DialogActions>
            <FormControl>
              <CreateUserButton size="large" endIcon={<PersonAddAltIcon />} type="submit">
                CHANGE
              </CreateUserButton>
            </FormControl>
          </DialogActions>
        </form>
      </Dialog>
      {resetPasswordStatus && (
        <Container>
          <Snackbar
            open={openResetPasswordStatus}
            autoHideDuration={6000}
            anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
            onClose={(event, reason) => {
              if (reason === 'clickaway') {
                return;
              }
              setOpenResetPasswordStatus(false);
            }}>
            <Alert
              severity={resetPasswordStatus ? resetPasswordStatus : 'info'}
              variant="filled"
              sx={{ width: '100%' }}>
              {resetPasswordMessage}
            </Alert>
          </Snackbar>
        </Container>
      )}
    </div>
  );
}
