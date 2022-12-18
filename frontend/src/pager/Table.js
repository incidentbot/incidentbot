import React, { useState } from 'react';
import axios from 'axios';
import PropTypes from 'prop-types';

import {
  Alert,
  Box,
  IconButton,
  LinearProgress,
  Paper,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  Toolbar,
  Tooltip,
  Typography
} from '@mui/material';

import FilterListIcon from '@mui/icons-material/FilterList';
import RefreshIcon from '@mui/icons-material/Refresh';
import { visuallyHidden } from '@mui/utils';

import useToken from '../hooks/useToken';
import { apiUrl } from '../shared/Variables';

//import moment from 'moment';

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
    id: 'schedule_summary',
    numeric: false,
    disablePadding: false,
    label: 'Schedule'
  },
  {
    id: 'escalation_policy',
    numeric: false,
    disablePadding: false,
    label: 'Escalation Policy'
  },
  {
    id: 'escalation_level',
    numeric: false,
    disablePadding: false,
    label: 'Escalation Level'
  },
  {
    id: 'user',
    numeric: false,
    disablePadding: false,
    label: 'User'
  },
  {
    id: 'start',
    numeric: false,
    disablePadding: false,
    label: 'Start'
  },
  {
    id: 'end',
    numeric: false,
    disablePadding: false,
    label: 'End'
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
  order: PropTypes.oneOf(['asc', 'desc']).isRequired,
  orderBy: PropTypes.string.isRequired,
  onRequestSort: PropTypes.func.isRequired
};

const EnhancedTableToolbar = (props) => {
  return (
    <Toolbar
      sx={{
        pl: { sm: 2 },
        pr: { xs: 1, sm: 1 }
      }}>
      <Typography sx={{ flex: '1 1 100%' }} variant="h6" id="tableTitle" component="div">
        On-Call
      </Typography>
      <Tooltip title="Refresh">
        <IconButton onClick={() => props.runJob('update_pagerduty_oc_data')}>
          <RefreshIcon />
        </IconButton>
      </Tooltip>
      <Tooltip title="Filter list">
        <IconButton>
          <FilterListIcon />
        </IconButton>
      </Tooltip>
    </Toolbar>
  );
};

export default function OnCallTable(props) {
  const [order, setOrder] = useState('asc');
  const [orderBy, setOrderBy] = useState('schedule_summary');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(20);

  const [jobRunStatus, setJobRunStatus] = useState('');
  const [jobRunMessage, setJobRunMessage] = useState('');
  const [openJobRunStatus, setOpenJobRunStatus] = useState(false);
  const [waitingForSomething, setWaitingForSomething] = useState(false);

  const { token } = useToken();

  const handleRequestSort = (event, property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  let collectedDicts = [];
  for (const objs of Object.values(props.data.data)) {
    objs.forEach((obj) => collectedDicts.push(obj));
  }

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  //
  function runJob(jobID) {
    var url = apiUrl + '/job/run/' + jobID;
    setWaitingForSomething(true);
    axios({
      method: 'POST',
      url: url,
      headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }
    })
      .then(function () {
        setJobRunMessage(`Successfully refreshed on-call data.`);
        setJobRunStatus(`success`);
        setOpenJobRunStatus(true);
        setWaitingForSomething(false);
        props.setRefreshData(true);
      })
      .catch(function (error) {
        if (error.response) {
          setJobRunMessage(`Error refreshing on-call data: ${error.response.data.error}`);
          setJobRunStatus('error');
          setOpenJobRunStatus(true);
          setWaitingForSomething(false);
        } else if (error.request) {
          setJobRunMessage(`Error refreshing on-call data: ${error.response.data.error}`);
          setJobRunStatus('error');
          setOpenJobRunStatus(true);
          setWaitingForSomething(false);
        }
      });
  }

  // Avoid a layout jump when reaching the last page with empty rows.
  const emptyRows = page > 0 ? Math.max(0, (1 + page) * rowsPerPage - collectedDicts.length) : 0;

  return (
    <Box sx={{ width: '100%' }}>
      <Paper sx={{ width: '100%', mb: 2 }}>
        <EnhancedTableToolbar runJob={runJob} />
        {waitingForSomething && <LinearProgress />}
        <TableContainer>
          <Table sx={{ minWidth: 850 }} aria-labelledby="tableTitle" size="small">
            <EnhancedTableHead
              order={order}
              orderBy={orderBy}
              onRequestSort={handleRequestSort}
              rowCount={collectedDicts.length}
            />
            <TableBody>
              {collectedDicts.length > 0 ? (
                stableSort(collectedDicts, getComparator(order, orderBy))
                  .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                  .map((row) => {
                    return (
                      <TableRow hover tabIndex={-1} key={row.schedule_summary}>
                        <TableCell align="left" padding="normal">
                          {row.schedule_summary}
                        </TableCell>
                        <TableCell align="left" padding="normal">
                          {row.escalation_policy}
                        </TableCell>
                        <TableCell align="left" padding="normal">
                          {row.escalation_level}
                        </TableCell>
                        <TableCell align="left" padding="normal">
                          {row.user}
                        </TableCell>
                        <TableCell align="left" padding="normal">
                          {row.start}
                        </TableCell>
                        <TableCell align="left" padding="normal">
                          {row.end}
                        </TableCell>
                      </TableRow>
                    );
                  })
              ) : (
                <>
                  <TableRow
                    style={{
                      height: 33 * emptyRows
                    }}>
                    <TableCell colSpan={8}>
                      No on-call data was retrieved from the backend.
                    </TableCell>
                  </TableRow>
                </>
              )}
              {emptyRows > 0 && (
                <TableRow
                  style={{
                    height: 33 * emptyRows
                  }}>
                  <TableCell colSpan={6} />
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[10, 20, 30]}
          component="div"
          count={collectedDicts.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>
      {jobRunStatus && (
        <Snackbar
          open={openJobRunStatus}
          autoHideDuration={6000}
          onClose={(event, reason) => {
            if (reason === 'clickaway') {
              return;
            }
            setOpenJobRunStatus(false);
          }}>
          <Alert
            severity={jobRunStatus ? jobRunStatus : 'info'}
            variant="filled"
            sx={{ width: '100%' }}>
            {jobRunMessage}
          </Alert>
        </Snackbar>
      )}
      <Typography sx={{ flex: '1 1 100%' }} color="inherit" variant="subtitle2" component="div">
        <i>Last Updated at: {props.data.ts}</i>
      </Typography>
    </Box>
  );
}
