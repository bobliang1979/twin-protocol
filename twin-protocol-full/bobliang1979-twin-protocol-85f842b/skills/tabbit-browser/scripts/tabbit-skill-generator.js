// Tabbit Skill 模板生成器
class TabbitSkillGenerator {
  static promptSkill(name, trigger, template) {
    return { type: "prompt", name, trigger, template, version: "1.0.0" };
  }
  static workflowSkill(name, trigger, steps) {
    return { type: "workflow", name, trigger, steps, version: "1.0.0" };
  }
  static export(skill) {
    return JSON.stringify(skill, null, 2);
  }
}
module.exports = { TabbitSkillGenerator };
