export interface ComparableRef {
  comparable_id: string;
  address: string;
  sale_price: string | null;
  rate_per_unit: string | null;
}

export interface FigureProvenance {
  valuation_line_id: string;
  label: string;
  amount: string;
  basis: string | null;
  source_ref: Record<string, unknown> | null;
  comparables: ComparableRef[];
}

export interface DocumentProvenance {
  document_id: string;
  kind: string;
  doc_date: string | null;
  issuing_authority: string | null;
  s3_key: string | null;
}

export interface ProvenanceSection {
  section_id: string;
  ord: number;
  section_type: string;
  content: string;
  figures: FigureProvenance[];
  documents: DocumentProvenance[];
}

export interface DeliverableProvenance {
  deliverable_id: string;
  doc_type: string;
  title: string;
  status: string;
  sections: ProvenanceSection[];
}

export interface DeliverableSummary {
  id: string;
  doc_type: string;
  title: string;
  status: string;
  mandate_id: string | null;
  created_at: string | null;
}
