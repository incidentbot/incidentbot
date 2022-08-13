import UserManagementMenu from './User-management-button.component';
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from '@mui/material';

import UserAddModal from './User-add-modal.component';

export default function UsersDisplay(props) {
  return (
    <div>
      <TableContainer component={Paper}>
        <Table sx={{ minWidth: 700 }} aria-label="simple table">
          <TableHead>
            <TableRow>
              <TableCell align="left">{`ID`}</TableCell>
              <TableCell align="left">Name</TableCell>
              <TableCell align="left">Email</TableCell>
              <TableCell align="left">Role</TableCell>
              <TableCell align="left">Administrator</TableCell>
              <TableCell align="left">Disabled</TableCell>
              <TableCell align="left">Settings</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {props.users.length ? (
              props.users.map((user) => (
                <TableRow key={user.id} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                  <TableCell component="th" scope="row">
                    {user.id}
                  </TableCell>
                  <TableCell align="left" padding="normal">
                    {user.name}
                  </TableCell>
                  <TableCell align="left" padding="normal">
                    {user.email}
                  </TableCell>
                  <TableCell align="left" padding="normal">
                    {user.role}
                  </TableCell>
                  <TableCell align="left" padding="normal">
                    {user.is_admin.toString()}
                  </TableCell>
                  <TableCell align="left" padding="normal">
                    {user.is_disabled.toString()}
                  </TableCell>
                  <TableCell padding="none">
                    <UserManagementMenu
                      user={user}
                      apiUrl={props.apiUrl}
                      setRefreshData={props.setRefreshData.bind()}
                    />
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow
                key={`no_users_row`}
                sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                <TableCell component="th" scope="row">
                  None
                </TableCell>
                <TableCell align="left">None</TableCell>
              </TableRow>
            )}
            <TableRow sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
              <UserAddModal apiUrl={props.apiUrl} setRefreshData={props.setRefreshData.bind()} />
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  );
}
