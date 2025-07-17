import React, { useState } from 'react';
import { Tooltip } from './ui/tooltip';
import { Badge } from './ui/badge';
import { InfoIcon } from 'lucide-react';

interface SanadBadgeProps {
  grade: string;
  certainty: number;
  showDetails?: boolean;
  scholarAttestations?: string[];
}

const GRADE_LABELS = {
  "THIQAH_THABIT": {
    arabic: "ثقة ثبت",
    tier: "Platinum",
    english: "Highest Reliability",
    color: "#FFD700",
    description: "Extremely reliable and precise - based on 1,400-year Islamic scholarly methodology"
  },
  "THIQAH": {
    arabic: "ثقة", 
    tier: "Gold",
    english: "Reliable",
    color: "#FFA500",
    description: "Reliable source with consistent accuracy"
  },
  "SADUQ": {
    arabic: "صدوق",
    tier: "Silver", 
    english: "Truthful",
    color: "#C0C0C0",
    description: "Truthful and honest evaluation"
  },
  "LA_BASH_BIHI": {
    arabic: "لا بأس به",
    tier: "Bronze",
    english: "Acceptable", 
    color: "#CD7F32",
    description: "No significant issues identified"
  },
  "LAYYIN": {
    arabic: "لين",
    tier: "Tier C",
    english: "Weak",
    color: "#FFA07A",
    description: "Some reliability concerns noted"
  },
  "FIHI_NAZAR": {
    arabic: "فيه نظر", 
    tier: "Tier D",
    english: "Questionable",
    color: "#FFB6C1",
    description: "Significant doubt about reliability"
  },
  "DAIF": {
    arabic: "ضعيف",
    tier: "Tier F", 
    english: "Unreliable",
    color: "#FF6B6B",
    description: "Low reliability, use with caution"
  }
} as const;

export function SanadBadge({ grade, certainty, showDetails = true, scholarAttestations = [] }: SanadBadgeProps) {
  const [showMethodology, setShowMethodology] = useState(false);
  const gradeInfo = GRADE_LABELS[grade as keyof typeof GRADE_LABELS];
  
  if (!gradeInfo) {
    return <Badge variant="secondary">Unknown Grade</Badge>;
  }

  const confidencePercentage = Math.round(certainty * 100);

  return (
    <div className="flex items-center gap-2">
      {/* Main Badge with Triple-Label Pattern */}
      <Badge 
        className="flex flex-col items-center px-3 py-2 min-w-[120px]"
        style={{ backgroundColor: gradeInfo.color, color: '#000' }}
      >
        <span className="font-bold text-sm">{gradeInfo.arabic}</span>
        <span className="text-xs font-medium">{gradeInfo.tier}</span>
        <span className="text-xs">{gradeInfo.english}</span>
      </Badge>

      {/* Confidence Indicator */}
      <div className="flex items-center gap-1">
        <span className="text-sm text-gray-600">
          {confidencePercentage}% confidence
        </span>
        
        {showDetails && (
          <Tooltip 
            content={
              <div className="max-w-xs">
                <div className="font-semibold mb-2">{gradeInfo.description}</div>
                <div className="text-xs space-y-1">
                  <div><strong>Methodology:</strong> Islamic ʿIlm al-Rijāl (1,400 years refined)</div>
                  <div><strong>Consensus:</strong> {confidencePercentage}% agent agreement</div>
                  {scholarAttestations.length > 0 && (
                    <div><strong>Scholar Attestations:</strong> {scholarAttestations.length} verified</div>
                  )}
                </div>
                <button 
                  onClick={() => setShowMethodology(true)}
                  className="text-blue-500 hover:text-blue-700 text-xs mt-2 underline"
                >
                  Learn more about Islamic methodology →
                </button>
              </div>
            }
          >
            <InfoIcon className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
          </Tooltip>
        )}
      </div>

      {/* Islamic Methodology Explainer Modal */}
      {showMethodology && (
        <IslamicMethodologyModal 
          onClose={() => setShowMethodology(false)}
          currentGrade={grade}
        />
      )}
    </div>
  );
}

// Modal component for Islamic methodology explanation
function IslamicMethodologyModal({ onClose, currentGrade }: { onClose: () => void; currentGrade: string }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-xl font-bold">Islamic ʿIlm al-Rijāl Methodology</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>
        
        <div className="space-y-4 text-sm">
          <div>
            <h3 className="font-semibold mb-2">What is ʿIlm al-Rijāl?</h3>
            <p>
              ʿIlm al-Rijāl is the Islamic science of evaluating the reliability of knowledge sources, 
              refined over 1,400 years by Islamic scholars. It's considered one of the most sophisticated 
              knowledge evaluation methodologies ever developed.
            </p>
          </div>
          
          <div>
            <h3 className="font-semibold mb-2">Why We Use It</h3>
            <p>
              This methodology provides unparalleled precision in assessing source reliability through:
            </p>
            <ul className="list-disc ml-4 mt-1">
              <li>Conditional reliability assessment (context-dependent trust)</li>
              <li>Temporal reliability tracking (changes over time)</li>
              <li>Multi-dimensional evaluation criteria</li>
              <li>Sophisticated consensus building (ijmāʿ)</li>
            </ul>
          </div>
          
          <div>
            <h3 className="font-semibold mb-2">Your Current Grade: {GRADE_LABELS[currentGrade as keyof typeof GRADE_LABELS]?.arabic}</h3>
            <p>{GRADE_LABELS[currentGrade as keyof typeof GRADE_LABELS]?.description}</p>
          </div>
          
          <div className="bg-blue-50 p-3 rounded">
            <p className="text-xs">
              <strong>Competitive Advantage:</strong> This methodology cannot be replicated without 
              deep Islamic scholarship, giving Sanad an unassailable competitive moat while ensuring 
              the highest standards of knowledge verification.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
} 