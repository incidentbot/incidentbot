import React, { useState } from 'react';
import axios from 'axios';

import { Avatar, ListItemIcon, Menu, MenuItem } from '@mui/material';
import { deepOrange } from '@mui/material/colors';

import { apiUrl } from '../shared/Variables';
import useToken from '../hooks/useToken';
import useUserData from '../hooks/useUserData';

import Logout from '@mui/icons-material/Logout';

function logOut(token, removeUserData, removeToken) {
  var url = apiUrl + '/user/logout';

  removeToken();
  removeUserData();

  axios({
    method: 'DELETE',
    url: url,
    headers: {
      Authorization: 'Bearer ' + token
    }
  })
    .then(() => {
      window.location.reload();
    })
    .catch((error) => {
      if (error.response) {
        console.log(error.response);
        console.log(error.response.status);
        console.log(error.response.headers);
      }
    });
}

export default function AvatarMenu() {
  const [anchorEl, setAnchorEl] = useState(null);

  const { userData } = useUserData();
  const { token, removeToken } = useToken();
  const { removeUserData } = useUserData();

  let userDataObj = JSON.parse(userData);

  const handleMenu = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <div>
      {userDataObj ? (
        <>
          <Avatar onClick={handleMenu} sx={{ bgcolor: deepOrange[500], marginLeft: 2 }}>
            {userDataObj.name.charAt(0).toUpperCase()}
          </Avatar>
          <Menu
            id="menu-appbar"
            anchorEl={anchorEl}
            anchorOrigin={{
              vertical: 'top',
              horizontal: 'right'
            }}
            keepMounted
            transformOrigin={{
              vertical: 'top',
              horizontal: 'right'
            }}
            open={Boolean(anchorEl)}
            onClose={handleClose}>
            <MenuItem>
              <Avatar sx={{ marginRight: 1 }} /> {userDataObj.name}
            </MenuItem>
            <MenuItem onClick={() => logOut(token, removeUserData, removeToken)}>
              <ListItemIcon>
                <Logout fontSize="small" />
              </ListItemIcon>
              Logout
            </MenuItem>
          </Menu>
        </>
      ) : (
        <Avatar sx={{ bgcolor: deepOrange[500], marginLeft: 2 }}></Avatar>
      )}
    </div>
  );
}
