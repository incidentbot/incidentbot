import React, { useState } from 'react';
import axios from 'axios';
import {
  Alert,
  Box,
  Button,
  Container,
  DialogActions,
  FormControl,
  IconButton,
  Input,
  InputLabel,
  Popover,
  Snackbar,
  Tooltip
} from '@mui/material';

import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import AddIcon from '@mui/icons-material/Add';
import useToken from '../../hooks/useToken';

export default function AddTagButton(props) {
  const [fetchStatus, setFetchStatus] = useState('');
  const [fetchMessage, setFetchMessage] = useState('');
  const [openFetchStatus, setOpenFetchStatus] = useState(false);

  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const { token } = useToken();

  const [values, setValues] = useState({
    tag: ''
  });

  const handleChange = (prop) => (event) => {
    setValues({ ...values, [prop]: event.target.value });
  };

  const handleOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  async function addTag() {
    await axios({
      method: 'PATCH',
      responseType: 'json',
      url: props.apiUrl + '/incident/' + props.incidentID,
      data: JSON.stringify({ field: 'tags', action: 'update', value: values.tag }),
      headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }
    })
      .then(function () {
        setFetchStatus('success');
        setFetchMessage(`Added tag.`);
        setOpenFetchStatus(true);
        props.setRefreshData(true);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error adding tag: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error adding tag: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  return (
    <div>
      <Tooltip title="Add a tag">
        <IconButton
          aria-describedby={'add-tag-dialog'}
          onClick={handleOpen}
          variant="contained"
          color="primary">
          <AddIcon />
        </IconButton>
      </Tooltip>
      <Popover
        id="add-tag-dialog"
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left'
        }}>
        <form onSubmit={() => addTag()}>
          <Box
            display="flex"
            sx={{
              height: 75,
              width: 300
            }}>
            <FormControl sx={{ m: 1, width: '100%' }} variant="standard">
              <InputLabel htmlFor="tag">Tag</InputLabel>
              <Input
                required
                id="tag"
                type="text"
                value={values.tag}
                onChange={handleChange('tag')}
                label="Tag"
              />
            </FormControl>
            <DialogActions sx={{ marginTop: 2 }}>
              <FormControl>
                <Button size="large" endIcon={<AddCircleOutlineIcon />} type="submit">
                  Add
                </Button>
              </FormControl>
            </DialogActions>
          </Box>
        </form>
      </Popover>
      {fetchStatus && (
        <Container>
          <Snackbar
            open={openFetchStatus}
            autoHideDuration={6000}
            anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
            onClose={(event, reason) => {
              if (reason === 'clickaway') {
                return;
              }
              setOpenFetchStatus(false);
            }}>
            <Alert
              severity={fetchStatus ? fetchStatus : 'info'}
              variant="filled"
              sx={{ width: '100%' }}>
              {fetchMessage}
            </Alert>
          </Snackbar>
        </Container>
      )}
    </div>
  );
}
