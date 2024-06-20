import { useState } from 'react';
import { Alert, Container, IconButton, Snackbar, TextField, Tooltip } from '@mui/material';
import { apiUrl } from '../../shared/Variables';
import useToken from '../../hooks/useToken';

import CloseIcon from '@mui/icons-material/Close';
import DoneIcon from '@mui/icons-material/Done';
import EditIcon from '@mui/icons-material/Edit';

export const EditableField = (props) => {
  const [editing, setEditing] = useState(false);
  const [fetchStatus, setFetchStatus] = useState('');
  const [fetchMessage, setFetchMessage] = useState('');
  const [openFetchStatus, setOpenFetchStatus] = useState(false);

  const { token } = useToken();

  const handleChange = (prop) => (event) => {
    setValues({ ...values, [prop]: event.target.value });
  };

  const handleEdit = () => {
    setEditing(true);
  };

  const handleCancel = () => {
    setEditing(false);
  };

  const [values, setValues] = useState({
    event: '',
    id: props.id
  });

  async function patchEvent(values) {
    return fetch(`${apiUrl}/incident/${props.incidentName}/audit`, {
      method: 'PATCH',
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(values)
    }).then((data) => data.json());
  }

  const handleSave = async (e) => {
    e.preventDefault();
    const event = await patchEvent({
      event: `${values.event}`,
      id: `${values.id}`
    });
    if (!event.success) {
      setFetchStatus('error');
      setFetchMessage(`Error editing event: ${event.error}`);
      setOpenFetchStatus(true);
    } else if (event.success) {
      setFetchStatus('success');
      setFetchMessage('Event edited successfully!');
      setOpenFetchStatus(true);
      setEditing(false);
      props.setRefreshData(true);
    }
  };

  return (
    <>
      {!editing ? (
        <>
          {props.event}
          <Tooltip title="Edit">
            <IconButton onClick={handleEdit} aria-label="edit">
              <EditIcon fontSize="small" color="info" />
            </IconButton>
          </Tooltip>
        </>
      ) : (
        <>
          <TextField
            variant="standard"
            defaultValue={props.event}
            fullWidth
            onChange={handleChange('event')}
          />
          <Tooltip title="Save">
            <IconButton onClick={handleSave} aria-label="save">
              <DoneIcon fontSize="small" color="info" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Cancel">
            <IconButton onClick={handleCancel} aria-label="cancel">
              <CloseIcon fontSize="small" color="error" />
            </IconButton>
          </Tooltip>
        </>
      )}
      {fetchStatus && (
        <Container>
          <Snackbar
            open={openFetchStatus}
            autoHideDuration={6000}
            anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
            onClose={(reason) => {
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
    </>
  );
};
