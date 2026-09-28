import { Routes, Route, Navigate, useLocation } from 'react-router';
import { AppShell } from '@/components/layout/AppShell';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { EDITORS, REVIEWERS } from '@/types';

// Page imports
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import DocumentsPage from '@/pages/DocumentsPage';
import DocumentPage from '@/pages/DocumentPage';
import ImpactPage from '@/pages/ImpactPage';
import RolesPage from '@/pages/RolesPage';
import EmployeesPage from '@/pages/EmployeesPage';
import MatrixPage from '@/pages/MatrixPage';
import VerificationPage from '@/pages/VerificationPage';
import PlansPage from '@/pages/PlansPage';
import PlanPage from '@/pages/PlanPage';
import EditItemPage from '@/pages/EditItemPage';
import ComparePage from '@/pages/ComparePage';
import UpdatePlanPage from '@/pages/UpdatePlanPage';
import JobPage from '@/pages/JobPage';
import ExperimentPage from '@/pages/ExperimentPage';
import LearningHomePage from '@/pages/LearningHomePage';
import LearnPage from '@/pages/LearnPage';
import AssessmentsPage from '@/pages/AssessmentsPage';
import ReportsPage from '@/pages/ReportsPage';
import AuditPage from '@/pages/AuditPage';
import UsersPage from '@/pages/UsersPage';
import NotFoundPage from '@/pages/NotFoundPage';
import WorkspacePage from '@/pages/WorkspacePage';
import RecoveryPage from '@/pages/RecoveryPage';
import RulePage from '@/pages/RulePage';

function RequirementsRedirect() {
  const { search, hash } = useLocation();
  return <Navigate to={`/matrix${search}${hash}`} replace />;
}

export default function App() {
  const editorsAndReviewers = [...EDITORS, ...REVIEWERS];
  
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<RecoveryPage />} />
      <Route path="/reset-password" element={<RecoveryPage />} />
      
      <Route path="/" element={<AppShell />}>
        {/* All roles */}
        <Route element={<ProtectedRoute />}>
          <Route path="search" element={<WorkspacePage mode="search" />} />
          <Route path="insights" element={<WorkspacePage mode="insights" />} />
          <Route index element={<DashboardPage />} />
          <Route path="employees" element={<EmployeesPage />} />
          <Route path="plans" element={<PlansPage />} />
          <Route path="plans/:id" element={<PlanPage />} />
          <Route path="plans/:id/compare" element={<ComparePage />} />
          <Route path="jobs/:id" element={<JobPage />} />
          <Route path="learning" element={<LearningHomePage />} />
          <Route path="learning/:planId" element={<LearnPage />} />
          <Route path="reports" element={<ReportsPage />} />
        </Route>

        {/* Editors & Reviewers */}
        <Route element={<ProtectedRoute allowedRoles={editorsAndReviewers} />}>
          <Route path="compare" element={<WorkspacePage mode="compare" />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="documents/:id" element={<DocumentPage />} />
          <Route path="documents/:id/impact" element={<ImpactPage />} />
          <Route path="roles" element={<RolesPage />} />
          <Route path="matrix" element={<MatrixPage />} />
          <Route path="requirements" element={<RequirementsRedirect />} />
          <Route path="verification" element={<VerificationPage />} />
          <Route path="plans/:planId/items/:reqId/edit" element={<EditItemPage />} />
          <Route path="plans/:id/update" element={<UpdatePlanPage />} />
          <Route path="experiments/:id" element={<ExperimentPage />} />
        </Route>

        {/* Reviewers & Manager */}
        <Route element={<ProtectedRoute allowedRoles={[...REVIEWERS, 'manager']} />}>
          <Route path="assessments" element={<AssessmentsPage />} />
        </Route>

        {/* Reviewers Only */}
        <Route element={<ProtectedRoute allowedRoles={[...REVIEWERS]} />}>
          <Route path="review-queue" element={<WorkspacePage mode="review-queue" />} />
          <Route path="requirements/:id/rules" element={<RulePage />} />
          <Route path="audit" element={<AuditPage />} />
        </Route>

        {/* Admin Only */}
        <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
          <Route path="settings" element={<WorkspacePage mode="settings" />} />
          <Route path="users" element={<UsersPage />} />
        </Route>
        <Route element={<ProtectedRoute allowedRoles={[...EDITORS]} />}>
          <Route path="manage" element={<WorkspacePage mode="manage" />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
