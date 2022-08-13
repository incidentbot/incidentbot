import React, { useEffect, useState } from 'react';
import axios from 'axios';

import { useTheme } from '@mui/material/styles';
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  OutlinedInput,
  Select,
  Snackbar
} from '@mui/material';

import useToken from '../../hooks/useToken';
import { apiUrl } from '../../shared/Variables';
import WaitingBase from '../../components/Waiting-base.component';

const ITEM_HEIGHT = 48;
const ITEM_PADDING_TOP = 8;

const MenuProps = {
  PaperProps: {
    style: {
      maxHeight: ITEM_HEIGHT * 4.5 + ITEM_PADDING_TOP,
      width: 250
    }
  }
};

function getStyles(item, selected, theme) {
  return {
    fontWeight:
      selected.indexOf(item) === -1
        ? theme.typography.fontWeightRegular
        : theme.typography.fontWeightMedium
  };
}

export default function PagerAutoSelect(props) {
  const theme = useTheme();
  const [selected, setSelected] = useState([]);
  const [loadingData, setLoadingData] = useState(true);

  const [fetchStatus, setFetchStatus] = useState('');
  const [fetchMessage, setFetchMessage] = useState('');
  const [openFetchStatus, setOpenFetchStatus] = useState(false);

  const { token } = useToken();

  async function retrieve() {
    await axios({
      method: 'GET',
      responseType: 'json',
      url: apiUrl + '/pager/auto_map/store',
      headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }
    })
      .then(function (response) {
        setSelected(response.data.data.teams);
        setLoadingData(false);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving value: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving value: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  async function update(value) {
    await axios({
      method: 'PATCH',
      responseType: 'json',
      url: apiUrl + '/pager/auto_map/store',
      data: JSON.stringify({ value: value }),
      headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }
    })
      .then(function () {
        setFetchStatus('success');
        setFetchMessage(`Updated value.`);
        setOpenFetchStatus(true);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error updating value: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error updating value: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  const handleChange = (event) => {
    setSelected(selected);
    const {
      target: { value }
    } = event;
    setSelected(typeof value === 'string' ? value.split(',') : value);
  };

  // Retrieve on-call data
  useEffect(() => {
    retrieve();
  }, []);

  return (
    <div>
      {!loadingData ? (
        <>
          <FormControl sx={{ marginBottom: 2, width: '100%' }}>
            <InputLabel id="auto-page-chip-input">None</InputLabel>
            <Select
              labelId="auto-page-chip"
              id="auto-page-chip"
              multiple
              value={selected}
              onChange={handleChange}
              input={<OutlinedInput id="select-multiple-chip" label="Chip" />}
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((value) => (
                    <Chip key={value} label={value} />
                  ))}
                </Box>
              )}
              MenuProps={MenuProps}>
              {Object.entries(props.data).map((item, index) => (
                <MenuItem key={index} value={item[0]} style={getStyles(item, selected, theme)}>
                  {item[0]}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button variant="contained" onClick={() => update(selected)}>
            Submit
          </Button>
        </>
      ) : (
        <WaitingBase />
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
