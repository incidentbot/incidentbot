import React, { useState } from 'react';
import axios from 'axios';
import PropTypes from 'prop-types';
import { alpha } from '@mui/material/styles';

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

import DeleteIcon from '@mui/icons-material/Delete';
import { visuallyHidden } from '@mui/utils';

import { apiUrl } from '../shared/Variables';
import useToken from '../hooks/useToken';
import PowerSettingsNewIcon from '@mui/icons-material/PowerSettingsNew';
import TableFilterOptions from './components/Table-filter.component';
import TableSearch from '../components/Search.component';

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
    id: 'id',
    numeric: false,
    disablePadding: false,
    label: 'ID'
  },
  {
    id: 'job_name',
    numeric: false,
    disablePadding: false,
    label: 'Job Name'
  },
  {
    id: 'function',
    numeric: false,
    disablePadding: false,
    label: 'Function'
  },
  {
    id: 'trigger',
    numeric: false,
    disablePadding: false,
    label: 'Trigger'
  },
  {
    id: 'next_run',
    numeric: false,
    disablePadding: false,
    label: 'Next Run'
  },
  {
    id: 'run',
    numeric: false,
    disablePadding: false,
    label: 'Run'
  },
  {
    id: 'delete',
    numeric: false,
    disablePadding: false,
    label: 'Delete'
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
  onRequestSort: PropTypes.func.isRequired,
  order: PropTypes.oneOf(['asc', 'desc']).isRequired,
  orderBy: PropTypes.string.isRequired,
  rowCount: PropTypes.number.isRequired
};

const EnhancedTableToolbar = (props) => {
  const { dense, handleChangeDense, numSelected, setQuery } = props;

  return (
    <Toolbar
      sx={{
        pl: { sm: 2 },
        pr: { xs: 1, sm: 1 },
        ...(numSelected > 0 && {
          bgcolor: (theme) =>
            alpha(theme.palette.primary.main, theme.palette.action.activatedOpacity)
        })
      }}>
      {numSelected > 0 ? (
        <Typography sx={{ flex: '1 1 100%' }} color="inherit" variant="subtitle1" component="div">
          {numSelected} selected
        </Typography>
      ) : (
        <Typography sx={{ flex: '1 1 100%' }} variant="h6" id="tableTitle" component="div">
          Jobs
        </Typography>
      )}

      {numSelected > 0 ? (
        <Tooltip title="Delete">
          <IconButton>
            <DeleteIcon />
          </IconButton>
        </Tooltip>
      ) : (
        <>
          <Box
            sx={{
              display: 'inline-flex'
            }}>
            <TableSearch setQuery={setQuery.bind()} />
            <TableFilterOptions
              dense={dense}
              handleChangeDense={handleChangeDense}
              hoverMessage={`Table filter options`}
            />
          </Box>
        </>
      )}
    </Toolbar>
  );
};

EnhancedTableToolbar.propTypes = {
  dense: PropTypes.bool.isRequired,
  handleChangeDense: PropTypes.func.isRequired,
  setQuery: PropTypes.func.isRequired
};

export default function EnhancedTable(props) {
  const [order, setOrder] = useState('asc');
  const [orderBy, setOrderBy] = useState('job_id');
  const [page, setPage] = useState(0);
  const [dense, setDense] = useState(true);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [query, setQuery] = useState('');

  const [jobRunStatus, setJobRunStatus] = useState('');
  const [jobRunMessage, setJobRunMessage] = useState('');
  const [openJobRunStatus, setOpenJobRunStatus] = useState(false);
  const [waitingForSomething, setWaitingForSomething] = useState(false);

  const { token } = useToken();

  function runJob(jobID) {
    var url = apiUrl + '/job/run/' + jobID;
    setWaitingForSomething(true);
    axios({
      method: 'POST',
      url: url,
      headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }
    })
      .then(function () {
        setJobRunMessage(`Ran job ${jobID}.`);
        setJobRunStatus(`success`);
        setOpenJobRunStatus(true);
        setWaitingForSomething(false);
        props.setRefreshData(true);
      })
      .catch(function (error) {
        if (error.response) {
          setJobRunMessage(`Error running job ${jobID}: ${error.response.data.error}`);
          setJobRunStatus('error');
          setOpenJobRunStatus(true);
          setWaitingForSomething(false);
        } else if (error.request) {
          setJobRunMessage(`Error running job ${jobID}: ${error.response.data.error}`);
          setJobRunStatus('error');
          setOpenJobRunStatus(true);
          setWaitingForSomething(false);
        }
        props.setRefreshData(true);
      });
  }

  function deleteJob(jobID) {
    var url = apiUrl + '/job/run/' + jobID;
    setWaitingForSomething(true);
    axios({
      method: 'DELETE',
      url: url,
      headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }
    })
      .then(function () {
        setJobRunMessage(`Deleted job ${jobID}.`);
        setJobRunStatus(`success`);
        setOpenJobRunStatus(true);
        setWaitingForSomething(false);
        props.setRefreshData(true);
      })
      .catch(function (error) {
        if (error.response) {
          setJobRunMessage(`Error deleting job ${jobID}: ${error.response.data.error}`);
          setJobRunStatus('error');
          setOpenJobRunStatus(true);
          setWaitingForSomething(false);
        } else if (error.request) {
          setJobRunMessage(`Error deleting job ${jobID}: ${error.response.data.error}`);
          setJobRunStatus('error');
          setOpenJobRunStatus(true);
          setWaitingForSomething(false);
        }
        props.setRefreshData(true);
      });
  }

  // Table functions
  const handleRequestSort = (event, property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleChangeDense = (event) => {
    setDense(event.target.checked);
  };

  // Avoid a layout jump when reaching the last page with empty rows.
  const emptyRows = page > 0 ? Math.max(0, (1 + page) * rowsPerPage - filteredJobsData.length) : 0;

  // Render jobs based on requested options
  // i.e. hide resolved, etc.
  function filterData(query, jobs) {
    var r = jobs;
    if (query !== null) {
      r = r.filter((job) => job.id.includes(query));
    }
    return r;
  }

  const filteredJobsData = filterData(query, props.jobs);

  return (
    <Box sx={{ width: '100%' }}>
      <Paper sx={{ width: '100%', mb: 2 }}>
        <EnhancedTableToolbar
          dense={dense}
          handleChangeDense={handleChangeDense}
          setQuery={setQuery.bind()}
        />
        {waitingForSomething && <LinearProgress />}
        <TableContainer>
          <Table
            sx={{ minWidth: 750 }}
            aria-labelledby="tableTitle"
            size={dense ? 'small' : 'medium'}>
            <EnhancedTableHead
              order={order}
              orderBy={orderBy}
              onRequestSort={handleRequestSort}
              rowCount={filteredJobsData.length}>
              {' '}
            </EnhancedTableHead>
            <TableBody>
              {stableSort(filteredJobsData, getComparator(order, orderBy))
                .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                .map((row) => {
                  return (
                    <TableRow hover tabIndex={-1} key={row.id}>
                      <TableCell align="left" padding="normal">
                        {row.id}
                      </TableCell>
                      <TableCell align="left" padding="normal">
                        {row.name}
                      </TableCell>
                      <TableCell align="left" padding="normal">
                        {row.function}
                      </TableCell>
                      <TableCell align="left" padding="normal">
                        {row.trigger}
                      </TableCell>
                      <TableCell align="left" padding="normal">
                        {row.next_run}
                      </TableCell>
                      <TableCell align="left" padding="normal">
                        <Tooltip title="Run Now">
                          <IconButton onClick={() => runJob(row.id)}>
                            <PowerSettingsNewIcon fontSize="medium" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                      <TableCell align="left" padding="normal">
                        <Tooltip title="Delete">
                          <IconButton onClick={() => deleteJob(row.id)}>
                            <DeleteIcon fontSize="medium" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  );
                })}
              {emptyRows > 0 && (
                <TableRow
                  style={{
                    height: (dense ? 33 : 53) * emptyRows
                  }}>
                  <TableCell colSpan={6} />
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={filteredJobsData.length}
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
    </Box>
  );
}
