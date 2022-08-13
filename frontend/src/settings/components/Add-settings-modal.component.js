import React, { useState } from 'react';
import axios from 'axios';

import {
  Alert,
  Box,
  Button,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Slide,
  Snackbar,
  TextField,
  Typography
} from '@mui/material';

import AddOutlinedIcon from '@mui/icons-material/AddOutlined';
import { apiUrl } from '../../shared/Variables';
import useToken from '../../hooks/useToken';
import { tryParseJSONObject } from './Shared';
import CodeEditor from '@uiw/react-textarea-code-editor';

const Transition = React.forwardRef(function Transition(props, ref) {
  return <Slide direction="down" ref={ref} {...props} />;
});

export default function AddSettingSlide(props) {
  const [open, setOpen] = useState(false);
  const [settingName, setSettingName] = useState('');
  const [settingValue, setSettingValue] = useState('');
  const [settingDescription, setSettingDescription] = useState('');

  const [fetchStatus, setFetchStatus] = useState('');
  const [fetchMessage, setFetchMessage] = useState('');
  const [openFetchStatus, setOpenFetchStatus] = useState(false);

  const { token } = useToken();

  const addSetting = async (name, value, description) => {
    var url = apiUrl + '/setting/' + name;
    await axios({
      method: 'POST',
      responseType: 'json',
      url: url,
      data: JSON.stringify({ value: value, description: description }),
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    })
      .then(function () {
        props.setRefreshData(true);
        setOpen(false);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error adding setting: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error adding setting: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  };

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setSettingName('');
    setSettingValue('');
  };

  const handleCreate = (e) => {
    e.preventDefault();
    let isValidJson = tryParseJSONObject(settingValue);
    if (!isValidJson) {
      setFetchStatus('error');
      setFetchMessage(`Value ${settingValue} is not valid JSON.`);
      setOpenFetchStatus(true);
    } else {
      addSetting(settingName, settingValue, settingDescription);
      setSettingName('');
      setSettingValue('');
      setSettingDescription('');
    }
  };

  return (
    <div>
      <Button
        variant="outlined"
        endIcon={<AddOutlinedIcon />}
        onClick={handleClickOpen}
        sx={{ marginBottom: 1 }}>
        Add New
      </Button>
      <Dialog
        open={open}
        TransitionComponent={Transition}
        keepMounted
        onClose={handleClose}
        aria-describedby="alert-dialog-slide-description">
        <DialogTitle>{'Add a setting'}</DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-slide-description">
            This will add a new key/value pair to the application settings. Note that the value must
            be JSON.
          </DialogContentText>
        </DialogContent>
        <DialogContent>
          <form onSubmit={handleCreate} id="setting-entry">
            <Box sx={{ paddingBottom: 1 }}>
              <TextField
                required
                fullWidth
                value={settingName}
                label="Name"
                onChange={(e) => setSettingName(e.target.value)}
              />
            </Box>
            <Box>
              <TextField
                required
                fullWidth
                value={settingDescription}
                label="Description"
                onChange={(e) => setSettingDescription(e.target.value)}
              />
            </Box>
            <Box sx={{ paddingBottom: 1, paddingTop: 1 }}>
              <Typography
                variant="subtitle2"
                sx={{
                  display: { xs: 'none', sm: 'block' },
                  fontFamily: 'Roboto',
                  fontWeight: 100,
                  letterSpacing: '.1rem',
                  color: 'inherit',
                  marginLeft: 0.5,
                  marginBottom: 1
                }}>
                VALUE
              </Typography>
              <CodeEditor
                value={settingValue}
                language="json"
                onChange={(evn) => setSettingValue(evn.target.value)}
                padding={15}
                style={{
                  fontSize: 14,
                  backgroundColor: '',
                  fontFamily:
                    'ui-monospace,SFMono-Regular,SF Mono,Consolas,Liberation Mono,Menlo,monospace'
                }}
              />
            </Box>
          </form>
        </DialogContent>
        <DialogActions>
          <Button variant="contained" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button variant="contained" type="submit" form="setting-entry">
            Submit
          </Button>
        </DialogActions>
      </Dialog>
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
