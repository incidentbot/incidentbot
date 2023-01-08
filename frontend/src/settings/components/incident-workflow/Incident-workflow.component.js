import { useCallback, useState } from 'react';
import { Alert, Container } from '@mui/material';
import ReactFlow, {
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  Controls
} from 'react-flow-renderer';

import initialNodes from './nodes.js';
import initialEdges from './edges.js';

function Flow() {
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);

  const onNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [setNodes]
  );
  const onEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [setEdges]
  );

  return (
    <div style={{ paddingTop: '2vh', paddingBottom: '5vh' }}>
      <Container maxWidth="lg">
        <Alert severity="info" variant="outlined" sx={{ width: '100%', marginBottom: 2 }}>
          This is a visual representation of the process that is followed when an incident is
          initiated. <b>This is a beta implementation and for now is read-only.</b>
        </Alert>
        <Container style={{ width: '100%', height: '450px' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView>
            <Background />
            <Controls />
          </ReactFlow>
        </Container>
      </Container>
    </div>
  );
}

export default Flow;
