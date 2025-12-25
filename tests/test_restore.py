from pppoe_cred_helper.restore import RollbackPlan

def test_rollback_plan_order():
    history = []
    
    def action(name):
        history.append(name)

    plan = RollbackPlan()
    plan.push("First", action, "First")
    plan.push("Second", action, "Second")
    
    plan.execute()
    # Should be LIFO
    assert history == ["Second", "First"]

def test_rollback_plan_exception_safety():
    history = []
    
    def fail():
        raise RuntimeError("Oops")
    
    def success():
        history.append("Success")

    plan = RollbackPlan()
    plan.push("Success", success)
    plan.push("Fail", fail)
    
    # Should continue even if one fails
    plan.execute()
    assert history == ["Success"]
