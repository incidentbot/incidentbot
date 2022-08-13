import { useState } from 'react';
import axios from 'axios';
import useToken from '../../hooks/useToken';

import { Alert, Container, IconButton, Menu, MenuItem, Snackbar } from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';

export default function UserManagementMenu(props) {
  const { token } = useToken();

  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };

  const [editUserStatus, setEditUserStatus] = useState('');
  const [editUserMessage, setEditUserMessage] = useState('');
  const [openEditUserStatus, setOpenEditUserStatus] = useState(false);

  async function editUser(user, operation, value) {
    var url = props.apiUrl + '/user/change/' + user.id;
    await axios({
      method: `${operation === 'delete' ? 'DELETE' : 'PATCH'}`,
      responseType: 'json',
      url: url,
      data: `${value !== null && JSON.stringify({ set_to: value })}`,
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + token
      }
    })
      .then(function () {
        setEditUserMessage(`Successfully edited user ${user.name}.`);
        setEditUserStatus('success');
        setOpenEditUserStatus(true);
        props.setRefreshData(true);
      })
      .catch(function (error) {
        if (error.response) {
          setEditUserMessage(`Error editing user ${user.name}: ${error.response.data.error}`);
          setEditUserStatus('error');
          setOpenEditUserStatus(true);
        } else if (error.request) {
          setEditUserMessage(`Error editing user ${user.name}: ${error}`);
          setEditUserStatus('error');
          setOpenEditUserStatus(true);
        }
      });
  }

  return (
    <div>
      <IconButton
        id="um-button"
        aria-controls={open ? 'um-menu' : undefined}
        aria-haspopup="true"
        aria-expanded={open ? 'true' : undefined}
        onClick={handleClick}>
        <SettingsIcon />
      </IconButton>
      <Menu
        id="um-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{
          'aria-labelledby': 'um-button'
        }}>
        <MenuItem onClick={() => editUser(props.user, 'delete', null)}>Delete</MenuItem>
        <MenuItem
          onClick={() =>
            editUser(
              props.user,
              'toggle',
              `${props.user.is_disabled ? 'enabled' : 'disabled'}`,
              token
            )
          }>
          {props.user.is_disabled ? 'Enable' : 'Disable'}
        </MenuItem>
        <MenuItem
          onClick={() =>
            editUser(
              props.user,
              'toggle',
              `${props.user.is_admin ? 'remove_admin' : 'add_admin'}`,
              token
            )
          }>
          {props.user.is_admin ? 'Remove Administrator Privileges' : 'Add Administrator Privileges'}
        </MenuItem>
      </Menu>
      {editUserStatus && (
        <Container>
          <Snackbar
            open={openEditUserStatus}
            autoHideDuration={6000}
            onClose={(event, reason) => {
              if (reason === 'clickaway') {
                return;
              }
              setOpenEditUserStatus(false);
            }}>
            <Alert
              severity={editUserStatus ? editUserStatus : 'info'}
              variant="filled"
              sx={{ width: '100%' }}>
              {editUserMessage}
            </Alert>
          </Snackbar>
        </Container>
      )}
    </div>
  );
}
