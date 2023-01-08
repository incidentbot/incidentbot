import { MarkerType } from 'react-flow-renderer';

const initialEdges = [
  {
    id: 'e1-2',
    source: '1',
    target: '2',
    animated: true,
    markerEnd: {
      type: MarkerType.ArrowClosed
    }
  },
  {
    id: 'e2-3',
    source: '2',
    target: '3',
    animated: true,
    markerEnd: {
      type: MarkerType.ArrowClosed
    }
  },
  {
    id: 'e3-4',
    source: '3',
    target: '4',
    animated: true,
    markerEnd: {
      type: MarkerType.ArrowClosed
    }
  },
  {
    id: 'e4-5',
    source: '4',
    target: '5',
    animated: true,
    markerEnd: {
      type: MarkerType.ArrowClosed
    }
  },
  {
    id: 'e5-6',
    source: '5',
    target: '6',
    animated: true,
    markerEnd: {
      type: MarkerType.ArrowClosed
    }
  }
];

export default initialEdges;
