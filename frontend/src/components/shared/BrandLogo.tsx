import mark from '@/assets/skillsprint-mark.svg';

export function BrandLogo() {
  return <div className="flex items-center gap-2.5" aria-label="SkillSprint AI">
    <img src={mark} alt="" className="h-10 w-10 shrink-0 shadow-sm rounded-xl" />
    <span className="font-bold text-[22px] tracking-[-0.8px] text-ink">SkillSprint<span className="ml-1 text-[10px] tracking-wide align-top text-green">AI</span></span>
  </div>;
}
