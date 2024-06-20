import React, { useEffect, useState } from 'react';
import axios from 'axios';
import PropTypes from 'prop-types';

import {
  Alert,
  Box,
  Container,
  IconButton,
  Paper,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Tooltip
} from '@mui/material';

import DeleteForeverIcon from '@mui/icons-material/DeleteForever';

import { apiUrl } from '../../shared/Variables';
import { visuallyHidden } from '@mui/utils';

import AddTimelineEventModal from './Add-timeline-event-modal.component';
import { EditableField } from './Editable-field.component.js';
import useToken from '../../hooks/useToken';
import WaitingBase from '../../components/Waiting-base.component';

// import moment from 'moment';

function descendingComparator(a, b, orderBy) {
  if (b[orderBy] < a[orderBy]) {
    return -1;
  }
  if (b[orderBy] > a[orderBy]) {
    return 1;
  }
  return 0;
}

function getComparator(order, orderBy) {
  return order === 'desc'
    ? (a, b) => descendingComparator(a, b, orderBy)
    : (a, b) => -descendingComparator(a, b, orderBy);
}

function stableSort(array, comparator) {
  const stabilizedThis = array.map((el, index) => [el, index]);
  stabilizedThis.sort((a, b) => {
    const order = comparator(a[0], b[0]);
    if (order !== 0) {
      return order;
    }
    return a[1] - b[1];
  });
  return stabilizedThis.map((el) => el[0]);
}

const headCells = [
  {
    id: 'timestamp',
    numeric: false,
    disablePadding: false,
    label: 'Timestamp',
    width: '15%'
  },
  {
    id: 'event',
    numeric: false,
    disablePadding: false,
    label: 'Event'
  },
  {
    id: 'user',
    numeric: false,
    disablePadding: false,
    label: 'User'
  },
  {
    id: 'manage',
    numeric: false,
    disablePadding: false,
    label: 'Manage'
  }
];

function EnhancedTableHead(props) {
  const { order, orderBy, onRequestSort } = props;
  const createSortHandler = (property) => (event) => {
    onRequestSort(event, property);
  };

  return (
    <TableHead>
      <TableRow>
        {headCells.map((headCell) => (
          <TableCell
            key={headCell.id}
            align={headCell.numeric ? 'right' : 'left'}
            padding={headCell.disablePadding ? 'none' : 'normal'}
            width={headCell.width ? headCell.width : null}
            sortDirection={orderBy === headCell.id ? order : false}>
            <TableSortLabel
              active={orderBy === headCell.id}
              direction={orderBy === headCell.id ? order : 'asc'}
              onClick={createSortHandler(headCell.id)}>
              <b>{headCell.label}</b>
              {orderBy === headCell.id ? (
                <Box component="span" sx={visuallyHidden}>
                  {order === 'desc' ? 'sorted descending' : 'sorted ascending'}
                </Box>
              ) : null}
            </TableSortLabel>
          </TableCell>
        ))}
      </TableRow>
    </TableHead>
  );
}

EnhancedTableHead.propTypes = {
  onRequestSort: PropTypes.func.isRequired,
  order: PropTypes.oneOf(['asc', 'desc']).isRequired,
  orderBy: PropTypes.string.isRequired
};

export default function Timeline(props) {
  const [auditLogData, setAuditLogData] = useState([]);
  const { token } = useToken();

  const [loadingData, setLoadingData] = useState(true);
  const [refreshData, setRefreshData] = useState(false);

  const [fetchStatus, setFetchStatus] = useState('');
  const [fetchMessage, setFetchMessage] = useState('');
  const [openFetchStatus, setOpenFetchStatus] = useState(false);

  const [order, setOrder] = useState('asc');
  const [orderBy, setOrderBy] = useState('ts');

  const handleRequestSort = (event, property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  async function getIncidentAuditLog() {
    var url = apiUrl + '/incident/' + props.incidentName + '/audit';
    await axios({
      method: 'GET',
      responseType: 'json',
      url: url,
      headers: {
        Authorization: 'Bearer ' + token
      }
    })
      .then(function (response) {
        setAuditLogData(response.data.data);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving audit log from backend: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving audit log from backend: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  async function deleteFromIncidentAuditLog(incident_id, id, log) {
    var url = apiUrl + '/incident/' + props.incidentName + '/audit';
    await axios({
      method: 'DELETE',
      responseType: 'json',
      url: url,
      data: JSON.stringify({ incident_id: incident_id, id: id, log: log }),
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    })
      .then(function () {
        setFetchStatus('success');
        setFetchMessage(`Removed entry.`);
        setOpenFetchStatus(true);
        setRefreshData(true);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error removing entry: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error removing entry: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  // Retrieve incidents and users
  useEffect(() => {
    getIncidentAuditLog();
    setLoadingData(false);
  }, []);

  if (refreshData) {
    setLoadingData(true);
    setRefreshData(false);
    getIncidentAuditLog();
    setLoadingData(false);
  }

  return (
    <div>
      {!loadingData ? (
        <>
          <Box sx={{ width: '100%' }}>
            <Paper sx={{ width: '100%', mb: 2 }}>
              <TableContainer>
                <Table sx={{ minWidth: 750 }} aria-labelledby="timeline" size={'small'}>
                  <EnhancedTableHead
                    order={order}
                    orderBy={orderBy}
                    onRequestSort={handleRequestSort}
                    rowCount={auditLogData.length}
                  />
                  <TableBody>
                    {auditLogData.length > 0 ? (
                      stableSort(auditLogData, getComparator(order, orderBy)).map((row, i) => {
                        return (
                          <TableRow hover tabIndex={-1} key={i}>
                            <TableCell align="left" padding="normal" sx={{ maxWidth: '0' }}>
                              {row.ts}
                            </TableCell>
                            <TableCell align="left" padding="normal">
                              <EditableField
                                event={row.log}
                                id={row.id}
                                incidentName={props.incidentName}
                                setRefreshData={setRefreshData.bind()}
                              />
                            </TableCell>
                            <TableCell align="left" padding="checkbox">
                              {row.user}
                            </TableCell>
                            <TableCell padding="checkbox">
                              <Stack direction="row">
                                <Tooltip title="Delete">
                                  <IconButton
                                    aria-label="delete"
                                    onClick={() =>
                                      deleteFromIncidentAuditLog(row.incident_id, row.id, row.log)
                                    }>
                                    <DeleteForeverIcon fontSize="small" color="error" />
                                  </IconButton>
                                </Tooltip>
                              </Stack>
                            </TableCell>
                          </TableRow>
                        );
                      })
                    ) : (
                      <>
                        <TableRow>
                          <TableCell colSpan={4}>No events.</TableCell>
                        </TableRow>
                      </>
                    )}
                    <TableRow>
                      <TableCell colSpan={4}>
                        <AddTimelineEventModal
                          apiUrl={apiUrl}
                          incidentName={props.incidentName}
                          setRefreshData={setRefreshData.bind()}
                        />
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Box>
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
