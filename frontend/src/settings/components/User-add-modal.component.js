import React, { useState } from 'react';
import useToken from '../../hooks/useToken';
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
  OutlinedInput,
  Snackbar
} from '@mui/material';

import { styled } from '@mui/material/styles';
import { lightBlue } from '@mui/material/colors';

import PersonAddAltIcon from '@mui/icons-material/PersonAddAlt';
import SettingsIcon from '@mui/icons-material/Settings';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';

export default function UserAddModal(props) {
  const { token } = useToken();

  const [values, setValues] = useState({
    name: '',
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

  const [addUserStatus, setAddUserStatus] = useState('');
  const [addUserMessage, setAddUserMessage] = useState('');
  const [openAddUserStatus, setOpenAddUserStatus] = useState(false);

  async function addUser(values) {
    return fetch(`${props.apiUrl}/user/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + token
      },
      body: JSON.stringify(values)
    }).then((data) => data.json());
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    const user = await addUser({
      name: `${values.name}`,
      email: `${values.email}`,
      password: `${values.password}`
    });
    if (!user.success) {
      setAddUserStatus('error');
      setAddUserMessage(`Error creating user: ${user.error}`);
      setOpenAddUserStatus(true);
    } else if (user.success) {
      setAddUserStatus('success');
      setAddUserMessage('User created successfully!');
      setOpenAddUserStatus(true);
      setOpen(false);
      props.setRefreshData(true);
    }
  };

  return (
    <div>
      <Button
        onClick={handleOpen}
        variant="contained"
        endIcon={<SettingsIcon />}
        sx={{
          paddingLeft: 2,
          paddingRight: 2,
          marginLeft: 1,
          marginRight: 1,
          marginBottom: 1,
          marginTop: 1
        }}>
        Add User
      </Button>
      <Dialog open={open} onClose={handleClose}>
        <form onSubmit={handleSubmit}>
          <DialogTitle>Add User</DialogTitle>
          <DialogContent>
            You must provide the user their name and password after account creation. For
            administrator users, you can upgrade their account to administrator status after
            creation.
          </DialogContent>
          <DialogContent>
            <FormControl variant="outlined" fullWidth sx={{ marginBottom: 2 }}>
              <InputLabel htmlFor="email">Name</InputLabel>
              <OutlinedInput
                required
                id="name"
                type="text"
                value={values.name}
                onChange={handleChange('name')}
                label="Name"
              />
            </FormControl>
            <FormControl variant="outlined" fullWidth sx={{ marginBottom: 2 }}>
              <InputLabel htmlFor="email">Email</InputLabel>
              <OutlinedInput
                required
                id="email"
                type="email"
                value={values.email}
                onChange={handleChange('email')}
                label="Email"
              />
            </FormControl>
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
                CREATE
              </CreateUserButton>
            </FormControl>
          </DialogActions>
        </form>
      </Dialog>
      {addUserStatus && (
        <Container>
          <Snackbar
            open={openAddUserStatus}
            autoHideDuration={6000}
            anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
            onClose={(event, reason) => {
              if (reason === 'clickaway') {
                return;
              }
              setOpenAddUserStatus(false);
            }}>
            <Alert
              severity={addUserStatus ? addUserStatus : 'info'}
              variant="filled"
              sx={{ width: '100%' }}>
              {addUserMessage}
            </Alert>
          </Snackbar>
        </Container>
      )}
    </div>
  );
}
