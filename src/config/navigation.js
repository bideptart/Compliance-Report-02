import { LayoutDashboard, Users, Radio, BookCheck, Network, Ticket } from "lucide-react";

export const NAV_ITEMS = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard },
  { label: "Customers", path: "/customers", icon: Users },
  { label: "FCC Compliance", path: "/fcc-compliance", icon: Radio },
  { label: "RMD", path: "/rmd", icon: BookCheck },
  { label: "Intermediate Registry", path: "/intermediate-registry", icon: Network },
  { label: "Trouble Tickets", path: "/trouble-tickets", icon: Ticket },
];
