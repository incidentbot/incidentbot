import React, { useState } from 'react';
import axios from 'axios';
import { Alert, Chip, Container, Snackbar, Stack } from '@mui/material';
import LabelIcon from '@mui/icons-material/Label';

import useToken from '../hooks/useToken';

export default function TagStack(props) {
  const [fetchStatus, setFetchStatus] = useState('');
  const [fetchMessage, setFetchMessage] = useState('');
  const [openFetchStatus, setOpenFetchStatus] = useState(false);

  const { token } = useToken();

  let incidentID = props.incidentID;

  async function removeTag(incidentID, tag) {
    await axios({
      method: 'PATCH',
      responseType: 'json',
      url: props.apiUrl + '/incident/' + incidentID,
      data: JSON.stringify({ field: 'tags', action: 'delete', value: tag }),
      headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }
    })
      .then(function () {
        setFetchStatus('success');
        setFetchMessage(`Deleted tag.`);
        setOpenFetchStatus(true);
        props.setRefreshData(true);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error removing tag: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error removing tag: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  function tags(tags) {
    let renderedTags = [];
    tags.map((tag, i) => renderedTags.push({ key: i, label: tag }));
    return renderedTags;
  }

  let tagObjs = tags(props.tags);

  const handleDelete = (tagToDelete) => () => {
    removeTag(incidentID, tagToDelete.label);
  };

  return (
    <div>
      {tagObjs.length > 0 && (
        <Stack direction="row" spacing={1}>
          {tagObjs.map((data) => {
            return (
              <Chip
                color="default"
                key={data.key}
                label={data.label}
                icon={<LabelIcon />}
                onDelete={handleDelete(data)}
                sx={{
                  ':hover': {
                    bgcolor: 'primary.main',
                    color: 'white'
                  }
                }}
              />
            );
          })}
        </Stack>
      )}
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
