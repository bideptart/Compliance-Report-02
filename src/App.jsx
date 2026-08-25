import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Customers from "./pages/Customers";
import CustomerDetail from "./pages/CustomerDetail";
import FccCompliance from "./pages/FccCompliance";
import Rmd from "./pages/Rmd";
import IntermediateRegistry from "./pages/IntermediateRegistry";
import TroubleTickets from "./pages/TroubleTickets";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="customers" element={<Customers />} />
        <Route path="customers/:id" element={<CustomerDetail />} />
        <Route path="fcc-compliance" element={<FccCompliance />} />
        <Route path="rmd" element={<Rmd />} />
        <Route path="intermediate-registry" element={<IntermediateRegistry />} />
        <Route path="trouble-tickets" element={<TroubleTickets />} />
      </Route>
    </Routes>
  );
}
